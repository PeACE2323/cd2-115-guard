# CD2-115-Guard

CloudDrive2 上传任务秒传判定 / 超时拦截 / 延迟重试 + 115 云下载超时清理，
一体化 Web 管理面板，单容器开箱即用。

## 功能矩阵

| 模块 | 能力 |
|---|---|
| CD2 上传监控 | 高频轮询 `GetUploadFileList(getAll=true)`，维护 `first_seen_at` |
| **作用域过滤** | **只有命中规则的任务才记录**；如只监控含 `PT` 的源路径，其余任务完全不入库 |
| 规则引擎 | 源路径关键字（支持正则）/ 超时阈值 / 重试次数与间隔，多规则优先级 CRUD |
| 秒传判定 | 阈值内完成 → 写入 `instant_uploads` |
| 不能秒传 | 超时 → `CancelUploadFiles` 取消该文件的上传 → 写入重试队列 |
| **备份重试闭环** | 到点 → `BackupRestartWalkingThrough` 让备份重新扫描，缺失文件自动重传 |
| **Webhook 源路径补全** | 接入 CD2 `file_system_watcher`，用真实 `source_file` 补全 gRPC 缺失的源路径 |
| 115 云下载 | 定期拉取任务列表，超过阈值自动删除离线任务（不删源文件）并写日志 |
| WebUI | 仪表盘 / 规则 / 任务 / 115 云下载 / 系统设置 |

> **本系统的上传来源是 CD2 备份任务**。因此重试策略只有一种：取消该文件的
> 上传任务 → 等待间隔 → 触发备份重新扫描。暂停/恢复不会改变能否秒传，
> 所以不提供该分支。


## 目录结构

```text
cd2-115-guard/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI 入口 + 静态挂载 + 生命周期钩子
│   ├── config.py                # 路径/环境变量常量（DATA_DIR、DB 路径等）
│   ├── models.py                # SQLAlchemy 模型 + 建表 + 默认配置播种
│   ├── schemas.py               # Pydantic 请求/响应模型
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py              # 依赖注入（DB 会话、服务单例）
│   │   ├── dashboard.py         # 仪表盘聚合数据
│   │   ├── rules.py             # 规则 CRUD / 启停
│   │   ├── tasks.py             # 实时任务 / 秒传记录 / 重试队列操作
│   │   ├── p115.py              # 云下载列表 / 配置 / 取消日志
│   │   └── settings.py          # 系统设置 / 连接测试 / Token 获取
│   ├── services/
│   │   ├── __init__.py
│   │   ├── rules.py             # 规则匹配纯逻辑（无第三方依赖，可单测）
│   │   ├── webhook_parser.py    # CD2 webhook 数据解析（零依赖）
│   │   ├── webhook.py           # webhook 落库 + 源路径映射
│   │   ├── cd2_client.py        # CD2 gRPC 封装（Bearer / 断线重连 / 任务管理）
│   │   ├── p115_client.py       # 115 封装（异步 / check_response / 单条删除）
│   │   └── scheduler.py         # 监控与重试调度引擎（AsyncIOScheduler）
│   └── proto/
│       ├── __init__.py
│       ├── clouddrive.proto     # 内置官方 proto 副本
│       ├── clouddrive_pb2.py        # 构建时生成
│       └── clouddrive_pb2_grpc.py   # 构建时生成
├── static/
│   ├── index.html               # 单页 WebUI（Vue3 + TailwindCSS via CDN）
│   └── vendor/                  # 可选：离线时放置 CDN 兜底资源
├── tools/
│   ├── fetch_proto.py           # 拉取官方 proto + protoc 编译 + 导入修正
│   ├── check_proto.py           # proto 静态自检（无 protobuf 环境可用）
│   ├── check_backend.py         # 后端静态检查（未定义名/死导入/路由一致性）
│   └── check_ui.py              # 前端模板检查（setup 暴露 vs 模板引用）
├── docker/
│   ├── entrypoint.sh            # 数据卷初始化 + 首启编译 proto
│   └── install.sh               # 本地非 Docker 安装
├── docs/
│   ├── schema.sql               # 权威 DDL 参考
│   ├── API_NOTES.md             # 接口事实核查笔记（字段名/陷阱）
│   └── WEBHOOK.md               # CD2 webhook 接入指南
├── data/                        # 挂载卷：guard.db / 115-cookies.txt / logs/
├── tests/
│   ├── __init__.py
│   ├── run_all.py               # 一次跑完全部零依赖测试
│   ├── test_rules.py            # 规则匹配 / 状态机
│   ├── test_webhook.py          # webhook 解析
│   ├── test_scope.py            # 作用域过滤（只监控 PT 场景）
│   └── test_backup.py           # 备份匹配与重试策略
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## 快速开始

### 方式一：直接用预构建镜像（推荐）

镜像由 GitHub Actions 自动构建并发布到 GHCR：

```bash
docker run -d \
  --name cd2-115-guard \
  --restart unless-stopped \
  -p 8899:8899 \
  -e TZ=Asia/Shanghai \
  -v /path/to/cd2-115-guard-data:/app/data \
  ghcr.io/peace2323/cd2-115-guard:latest
```

打开 `http://<host>:8899`。

> GHCR 包默认是 private，首次拉取需先登录：
> `echo <你的PAT> | docker login ghcr.io -u PeACE2323 --password-stdin`
> 登录后到 GitHub → Packages → cd2-115-guard → Settings 把可见性改为 Public，
> 之后其他人也能直接拉取。

### 方式二：本地构建

```bash
docker compose up -d --build
```

首次启动后进入「系统设置」填写 CD2 地址与 Token、115 Cookie，点击「连接测试」确认，
再到「CD2 规则」新建一条监控规则即可开始工作。

WebUI 五个页面：

| 页面 | 内容 |
|---|---|
| 仪表盘 | CD2/115 连接状态、今日秒传、当前上传中、等待重试、今日云下载取消、调度任务 |
| CD2 规则 | 规则 CRUD、启停、关键字实时校验与命中预览 |
| 任务监控 | 实时上传列表 / 秒传详情 / 重试队列（支持批量重试、取消、删除） |
| 115 云下载 | 任务列表与驻留时长、超时标红、手动取消、取消日志 |
| 系统设置 | CD2 地址与 Token、账号换 Token、115 Cookie、Webhook、事件日志 |


数据持久化在该目录下的 `./data`，包含：

- `data/guard.db` —— SQLite 数据库
- `data/115-cookies.txt` —— 115 Cookie（权限 600）
- `data/logs/` —— 应用日志

## 关键配置项

在 WebUI「系统设置」中填写，或直接改数据库 `app_settings` 表：

| 键 | 说明 | 默认 |
|---|---|---|
| `cd2.host` | CD2 gRPC 地址 `host:port` | `clouddrive2:19799` |
| `cd2.token` | CD2 Bearer Token | 空 |
| `cd2.poll_interval` | 上传任务轮询间隔（秒） | 3 |
| `p115.cookie` | 115 Cookie | 空 |
| `p115.poll_interval` | 云下载轮询间隔（秒） | 300 |
| `p115.timeout_threshold` | 云下载最大允许耗时（秒） | 86400 |
| `p115.auto_cancel` | 是否自动取消 | 1 |

> CD2 的 gRPC 端口默认是 **19799**（Web UI 走 19798），请勿填错。

## 重试闭环（基于 CD2 备份任务）

本系统的上传由 **CD2 备份任务**产生（源目录 → 云盘目标目录）。因此超时处理是：

```text
上传耗时 > 规则阈值
   ↓
CancelUploadFiles(该文件的 task.key)      ← 只取消这 1 个文件，不动整个备份
   ↓ 等待 retry_interval
BackupGetAll → 找到该文件所属备份
   ↓
BackupRestartWalkingThrough(备份源目录)   ← 让备份重新扫描
   ↓
备份比对目标端 → 缺失文件重新上传 → 再次走秒传判定
```

设计要点：

- **只取消单个任务**，不用 `BackupSetEnabled(false)` 停整个备份，避免波及同一备份下的其他文件；
- **嵌套备份取最长匹配**：`/mnt/PT/movies` 优于 `/mnt/PT`；
- **`/mnt/PT` 不会误匹配 `/mnt/PT2`**（目录前缀已在测试中固化）；
- 找不到所属备份时回退到 `CopyFile`，仍失败则标记 `failed` 并写 `event_logs`。

## 作用域过滤（只监控关心的上传）

**只有命中规则的 CD2 上传任务才会被记录和处理**，其余任务完全不进数据库、
不产生任何干预。例如只想监控源路径含 `PT` 的任务，只需建一条规则：

| 字段 | 值 |
|---|---|
| 规则名称 | PT 任务 |
| 源文件夹路径关键字 | `PT` |
| 超时阈值 | 60 秒 |
| 拦截动作 | pause |

于是 `/mnt/local/PT/**` 的上传会被监控，`/mnt/local/Docker/**` 的任务被完全忽略。

> ⚠️ 关键字是**子串**匹配，`PT` 也会命中 `apt`、`PTX` 等路径。
> 需要精确限定目录时，勾选「正则」并填 `/PT/` 或 `^/mnt/local/PT/`。

## CD2 Webhook 接入（推荐）

CD2 的 gRPC 上传任务**不含源路径**，也没有“重新上传本地文件”的 RPC。
接入 `file_system_watcher` webhook 后，两个缺口都能补上：

1. 用真实 `source_file` 参与规则匹配（而不是拿 `destPath` 猜）；
2. `cancel_reupload` 策略可据此真正重新触发上传。

服务端已提供接收端点，在 CD2 配置文件的 `[global_params]` 中把
`base_url` 指向本服务，并启用 `[file_system_watcher]` 即可：

```toml
[global_params]
base_url = "http://192.168.1.10:8899"
enabled = true

[file_system_watcher]
url = "{base_url}/api/webhook/cd2/file_notify?device_name={device_name}&user_name={user_name}"
method = "POST"
enabled = true
# body 使用 CD2 官方模板原样即可，见 docs/WEBHOOK.md
```

完整配置模板、字段语义与安全说明见 [docs/WEBHOOK.md](docs/WEBHOOK.md)。

## 开发

```bash
bash docker/install.sh          # 建 venv、装依赖、编译 proto
. .venv/bin/activate
uvicorn app.main:app --reload --port 8899
```

零依赖单元测试（无需装 sqlalchemy / grpcio / p115client）：

```bash
python tests/run_all.py
```

应用启动冒烟测试（会真实 import 应用并请求关键接口，需要先装依赖）：

```bash
pip install -r requirements.txt
python tools/fetch_proto.py --out app/proto --offline
python tests/test_smoke.py
```

静态检查（同样不依赖第三方库，适合 CI 前置校验）：

```bash
python tools/check_backend.py                    # 未定义名 / 死导入 / 路由一致性
python tools/check_fastapi.py                    # 路由返回注解是否会被当 Pydantic 模型
python tools/check_ui.py static/index.html       # Vue 模板引用完整性
python tools/check_proto.py app/proto/clouddrive.proto
```

单独编译 / 校验 proto：

```bash
python tools/fetch_proto.py --out app/proto           # 拉取官方最新版并编译
python tools/fetch_proto.py --out app/proto --offline # 仅用内置副本编译
python tools/check_proto.py app/proto/clouddrive.proto
```

## 排查

```bash
sqlite3 data/guard.db "select * from event_logs order by id desc limit 20;"
sqlite3 data/guard.db "select status,count(*) from non_instant_tasks group by status;"
docker compose logs -f cd2-115-guard
```
