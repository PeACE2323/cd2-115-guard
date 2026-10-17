#!/usr/bin/env sh
# =============================================================================
# CD2-115-Guard entrypoint
#   - ensures the data volume layout exists
#   - compiles clouddrive.proto on first boot if the image shipped without it
#     (useful when the image is built with --build-arg SKIP_PROTO=1)
#   - then execs the CMD (uvicorn)
# =============================================================================
set -eu

DATA_DIR="${DATA_DIR:-/app/data}"

mkdir -p "${DATA_DIR}" "${DATA_DIR}/logs"
touch "${DATA_DIR}/.keep" 2>/dev/null || true

# ---- 115 cookies 文件权限收敛（只允许属主读写） ----
COOKIE_FILE="${DATA_DIR}/115-cookies.txt"
if [ -f "${COOKIE_FILE}" ]; then
  chmod 600 "${COOKIE_FILE}" 2>/dev/null || true
fi

# ---- 首次启动编译 proto ----
if [ ! -f "/app/app/proto/clouddrive_pb2_grpc.py" ]; then
  echo "[entrypoint] clouddrive_pb2*.py 缺失，开始编译 proto ..."
  python /app/tools/fetch_proto.py --out /app/app/proto --offline || {
    echo "[entrypoint] proto 编译失败，容器退出" >&2
    exit 1
  }
fi

# ---- 数据库路径兜底 ----
export GUARD_DB_PATH="${GUARD_DB_PATH:-${DATA_DIR}/guard.db}"

echo "[entrypoint] data dir : ${DATA_DIR}"
echo "[entrypoint] database  : ${GUARD_DB_PATH}"
echo "[entrypoint] starting  : $*"

exec "$@"
