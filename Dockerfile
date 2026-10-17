# syntax=docker/dockerfile:1
# =============================================================================
# CD2-115-Guard  —  CloudDrive2 upload guard + 115 offline-download reaper
# -----------------------------------------------------------------------------
# 注意：基础镜像必须是 Python >= 3.12，因为 p115client 声明 Requires-Python
#       >=3.12（3.11 上 pip 会直接拒绝安装）。
# =============================================================================
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Asia/Shanghai \
    APP_HOME=/app \
    DATA_DIR=/app/data \
    CD2_PROTO_URL=https://www.clouddrive2.com/api/clouddrive.proto

# ---- OS deps (curl for the proto fetch, tzdata for correct local time) ------
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl tzdata \
 && rm -rf /var/lib/apt/lists/*

WORKDIR ${APP_HOME}

# ---- Python deps first so the layer is cached across source edits -----------
COPY requirements.txt requirements-optional.txt ./

# 必需依赖：失败即中止
RUN pip install --upgrade pip \
 && pip install -r requirements.txt

# 可选依赖（115 相关）：失败只告警，不阻断构建。
# 这样即使某个可选包因版本/网络问题装不上，CD2 侧功能依然可用。
RUN pip install -r requirements-optional.txt \
 || echo "WARNING: 可选依赖(115 相关)安装失败，115 云下载功能将不可用"

# ---- Application sources ----------------------------------------------------
COPY . .

# ---- Compile clouddrive.proto -> clouddrive_pb2*.py ------------------------
# Uses the vendored proto by default; falls back to the official download,
# and finally to the pure-python descriptor builder if protoc is unavailable.
RUN python tools/fetch_proto.py --out app/proto

# ---- Non-root runtime user --------------------------------------------------
RUN useradd --create-home --uid 1000 appuser \
 && mkdir -p ${DATA_DIR} \
 && chown -R appuser:appuser ${APP_HOME} \
 && chmod +x docker/entrypoint.sh

USER appuser

VOLUME ["/app/data"]
EXPOSE 8899

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8899/api/health || exit 1

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8899", "--proxy-headers"]
