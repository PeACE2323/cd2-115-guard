"""全局路径与运行时常量。

所有可变状态都落在 DATA_DIR（Docker 挂载卷 /app/data）下：
    DATA_DIR/guard.db           SQLite 数据库
    DATA_DIR/115-cookies.txt    115 Cookie
    DATA_DIR/logs/              应用日志
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# 目录
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent          # 项目根
APP_DIR = BASE_DIR / "app"
STATIC_DIR = BASE_DIR / "static"
PROTO_DIR = APP_DIR / "proto"

DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR / "data")).resolve()
LOG_DIR = DATA_DIR / "logs"

DB_PATH = Path(os.environ.get("GUARD_DB_PATH", DATA_DIR / "guard.db")).resolve()
COOKIE_FILE = Path(
    os.environ.get("P115_COOKIE_FILE", DATA_DIR / "115-cookies.txt")
).resolve()

# SQLite 连接串（WAL + 容忍并发读）
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

# ---------------------------------------------------------------------------
# 默认值（首次启动写入 app_settings）
# ---------------------------------------------------------------------------
DEFAULT_SETTINGS: dict[str, str] = {
    "cd2.host": os.environ.get("CD2_DEFAULT_HOST", "clouddrive2:19799"),
    "cd2.token": "",
    "cd2.username": "",
    "cd2.password": "",
    "cd2.poll_interval": "3",
    "p115.cookie": "",
    "p115.poll_interval": "300",
    "p115.timeout_threshold": str(24 * 3600),
    "p115.auto_cancel": "1",
    "p115.task_page_size": "30",
    # CD2 webhook 鉴权令牌；留空表示不校验（内网快速接入）
    "webhook.token": "",
}

# ---------------------------------------------------------------------------
# CD2 上传任务状态枚举（UploadFileInfo.Status）
# ---------------------------------------------------------------------------
CD2_STATUS_NAMES: dict[int, str] = {
    0: "WaitforPreprocessing",
    1: "Preprocessing",
    2: "Cancelled",
    3: "Transfer",
    4: "Pause",
    5: "Finish",
    6: "Skipped",
    7: "Inqueue",
    8: "Ignored",
    9: "Error",
    10: "FatalError",
}

CD2_STATUS_FINISH = 5          # 秒传成功的判定依据
CD2_STATUS_CANCELLED = 2
CD2_STATUS_PAUSE = 4
CD2_STATUS_FAILED = {9, 10}    # Error / FatalError

# 仍在“进行中”的状态集合：用于计算已持续上传时间
CD2_STATUS_ACTIVE = {0, 1, 3, 7}

# ---------------------------------------------------------------------------
# 业务状态机
# ---------------------------------------------------------------------------
# non_instant_tasks.status
STATUS_WAITING = "waiting"      # 等待重试
STATUS_RETRYING = "retrying"    # 重试中
STATUS_SUCCESS = "success"      # 重试成功
STATUS_FAILED = "failed"        # 最终失败 / 已放弃
STATUS_CANCELLED = "cancelled"  # 用户取消重试

NON_INSTANT_ACTIVE_STATUSES = (STATUS_WAITING, STATUS_RETRYING)

# 规则：拦截动作 / 重试策略
#
# 本项目上传来自 **CD2 备份任务**，因此重试策略统一为：
#   取消该文件的上传任务 → 等待间隔 → BackupRestartWalkingThrough 让备份重扫
# 暂停/恢复（pause_resume）不适用于备份场景：暂停再恢复只是继续同一次上传，
# 不会改变“能否秒传”的结果，因此不再提供。
INTERCEPT_CANCEL = "cancel"
STRATEGY_CANCEL_REUPLOAD = "cancel_reupload"

# 保留这两个常量仅为兼容旧数据中的历史取值（读取时会被归一化为 cancel_reupload）
INTERCEPT_PAUSE = "pause"
STRATEGY_PAUSE_RESUME = "pause_resume"

# 115 云下载归一化状态
P115_ST_WAITING = "waiting"
P115_ST_DOWNLOADING = "downloading"
P115_ST_FINISHED = "finished"
P115_ST_FAILED = "failed"
P115_ST_CANCELLED = "cancelled"
P115_ST_REMOVED = "removed"

# 115 原始 status 中视为“已完成”的集合（待运行期实测校准）
P115_FINISHED_STATUS = {2, 11}
# 115 原始 status 中视为“任务已消失/已删除”的集合
P115_REMOVED_STATUS = {-1, 1}

# p115client 云下载列表 stat 参数：0=全部 9=失败 11=完成 12=进行中
P115_STAT_ALL = 0

# 115 原始 status 中视为“失败”的集合（stat=9 对应“已失败”）
P115_FAILED_STATUS = {9}

# 115 云下载列表接口基地址（clouddownload.115.com 为主，lixian.115.com 为历史别名）
P115_CLOUDDOWNLOAD_HOST = "https://clouddownload.115.com"
P115_LIXIAN_HOST = "https://lixian.115.com"

# ---------------------------------------------------------------------------
# 调度与容错参数
# ---------------------------------------------------------------------------
# CD2 gRPC 单次调用超时（秒）
CD2_RPC_TIMEOUT = 10.0
# 断开后重连的基础退避（秒）与上限
CD2_RECONNECT_BASE = 2.0
CD2_RECONNECT_MAX = 60.0
# 任务在 CD2 列表中连续消失多少秒后，才认定“已从队列移除”
TASK_GONE_GRACE_SEC = 120.0
# 单轮轮询最多处理多少条超时任务（防止积压时一次性打爆 CD2）
MAX_INTERCEPT_PER_ROUND = 20
# 单轮最多触发多少次重试
MAX_RETRY_PER_ROUND = 20
# 秒传记录/事件日志保留条数上限（防止数据库无限膨胀）
MAX_EVENT_LOGS = 5000

LOG_RETENTION_DAYS = 30
