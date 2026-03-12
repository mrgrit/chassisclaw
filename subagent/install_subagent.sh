#!/usr/bin/env bash
set -Eeuo pipefail

log()  { echo "[+] $*"; }
warn() { echo "[!] $*" >&2; }
die()  { echo "[x] $*" >&2; exit 1; }

if [[ "${EUID}" -ne 0 ]]; then
  die "run as root (ex: curl ... | sudo bash)"
fi

AGENT_ID=""
LISTEN_PORT="55123"
BIND_HOST="0.0.0.0"
INSTALL_ROOT="/opt/chassisclaw-subagent"
SERVICE_NAME="chassisclaw-subagent"
REPO_URL=""
BRANCH="main"
BUNDLE_URL=""
CORE_URL=""
TZ_NAME="Asia/Seoul"
FORCE_REINSTALL="false"

usage() {
  cat <<'EOF'
Usage:
  install_subagent.sh --agent-id ID [options]

Required:
  --agent-id ID

One of:
  --bundle-url URL
  --repo-url URL

Optional:
  --branch NAME
  --listen-port PORT
  --bind-host HOST
  --install-root DIR
  --service-name NAME
  --core-url URL
  --tz NAME
  --force-reinstall
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --agent-id) AGENT_ID="${2:-}"; shift 2 ;;
    --listen-port) LISTEN_PORT="${2:-}"; shift 2 ;;
    --bind-host) BIND_HOST="${2:-}"; shift 2 ;;
    --install-root) INSTALL_ROOT="${2:-}"; shift 2 ;;
    --service-name) SERVICE_NAME="${2:-}"; shift 2 ;;
    --repo-url) REPO_URL="${2:-}"; shift 2 ;;
    --branch) BRANCH="${2:-}"; shift 2 ;;
    --bundle-url) BUNDLE_URL="${2:-}"; shift 2 ;;
    --core-url) CORE_URL="${2:-}"; shift 2 ;;
    --tz) TZ_NAME="${2:-}"; shift 2 ;;
    --force-reinstall) FORCE_REINSTALL="true"; shift 1 ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

[[ -n "${AGENT_ID}" ]] || die "--agent-id is required"
if [[ -z "${BUNDLE_URL}" && -z "${REPO_URL}" ]]; then
  die "one of --bundle-url or --repo-url is required"
fi

export DEBIAN_FRONTEND=noninteractive

detect_pkg_mgr() {
  if command -v apt-get >/dev/null 2>&1; then
    echo "apt"; return
  fi
  if command -v dnf >/dev/null 2>&1; then
    echo "dnf"; return
  fi
  if command -v yum >/dev/null 2>&1; then
    echo "yum"; return
  fi
  die "unsupported package manager"
}

install_common_deps_apt() {
  apt-get update -y
  apt-get install -y ca-certificates curl git jq tar unzip gzip xz-utils python3 python3-venv gnupg lsb-release
}

docker_ok() {
  command -v docker >/dev/null 2>&1 && docker version >/dev/null 2>&1
}

docker_compose_ok() {
  docker compose version >/dev/null 2>&1
}

install_docker_apt() {
  log "installing Docker via official Docker repo"

  install -m 0755 -d /etc/apt/keyrings
  if [[ ! -f /etc/apt/keyrings/docker.gpg ]]; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
  fi

  local codename arch
  arch="$(dpkg --print-architecture)"
  codename="$(
    . /etc/os-release
    echo "${VERSION_CODENAME:-jammy}"
  )"

  cat > /etc/apt/sources.list.d/docker.list <<EOF
deb [arch=${arch} signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${codename} stable
EOF

  apt-get update -y

  # docker.io / old containerd package conflicts 방지
  apt-get remove -y docker.io docker-doc docker-compose podman-docker || true
  apt-get remove -y containerd runc || true

  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
}

ensure_docker_apt() {
  install_common_deps_apt

  if docker_ok; then
    log "docker already installed"
  else
    install_docker_apt
  fi

  if docker_compose_ok; then
    log "docker compose already available"
  else
    log "docker compose plugin missing; attempting install"
    install_docker_apt
    docker_compose_ok || die "docker compose plugin install failed"
  fi
}

ensure_docker_dnf() {
  dnf install -y ca-certificates curl git jq tar unzip gzip xz python3 docker
  systemctl enable --now docker
  docker_ok || die "docker install failed"
  docker_compose_ok || warn "docker compose plugin not found; compose-based startup may fail"
}

ensure_docker_yum() {
  yum install -y ca-certificates curl git jq tar unzip gzip xz python3 docker
  systemctl enable --now docker
  docker_ok || die "docker install failed"
  docker_compose_ok || warn "docker compose plugin not found; compose-based startup may fail"
}

ensure_prereqs() {
  local mgr
  mgr="$(detect_pkg_mgr)"
  case "${mgr}" in
    apt) ensure_docker_apt ;;
    dnf) ensure_docker_dnf ;;
    yum) ensure_docker_yum ;;
  esac
}

prepare_dirs() {
  if [[ "${FORCE_REINSTALL}" == "true" && -d "${INSTALL_ROOT}" ]]; then
    log "removing previous install dir: ${INSTALL_ROOT}"
    rm -rf "${INSTALL_ROOT}"
  fi

  mkdir -p "${INSTALL_ROOT}/src"
  mkdir -p "${INSTALL_ROOT}/run"
}

fetch_source_bundle() {
  local bundle_path="${INSTALL_ROOT}/run/source.bundle"
  log "downloading bundle: ${BUNDLE_URL}"
  curl -fsSL "${BUNDLE_URL}" -o "${bundle_path}"

  rm -rf "${INSTALL_ROOT}/src"/*
  case "${bundle_path}" in
    *.tar.gz|*.tgz)
      tar -xzf "${bundle_path}" -C "${INSTALL_ROOT}/src"
      ;;
    *.zip)
      unzip -q "${bundle_path}" -d "${INSTALL_ROOT}/src"
      ;;
    *)
      if tar -xzf "${bundle_path}" -C "${INSTALL_ROOT}/src" 2>/dev/null; then
        true
      elif unzip -q "${bundle_path}" -d "${INSTALL_ROOT}/src" 2>/dev/null; then
        true
      else
        die "unsupported bundle format: ${bundle_path}"
      fi
      ;;
  esac
}

fetch_source_repo() {
  local repo_dir="${INSTALL_ROOT}/src/repo"
  if [[ -d "${repo_dir}/.git" ]]; then
    log "updating repo"
    git -C "${repo_dir}" fetch --all --prune
    git -C "${repo_dir}" checkout "${BRANCH}"
    git -C "${repo_dir}" pull --ff-only origin "${BRANCH}"
  else
    log "cloning repo: ${REPO_URL}"
    rm -rf "${repo_dir}"
    git clone --branch "${BRANCH}" --depth 1 "${REPO_URL}" "${repo_dir}"
  fi
}

detect_source_root() {
  local p
  while IFS= read -r -d '' p; do
    if [[ -f "${p}/Dockerfile" || -f "${p}/docker-compose.yml" || -d "${p}/subagent" || -d "${p}/app" ]]; then
      echo "$p"
      return
    fi
  done < <(find "${INSTALL_ROOT}/src" -mindepth 1 -maxdepth 4 -type d -print0)

  echo "${INSTALL_ROOT}/src"
}

detect_dockerfile() {
  local root="$1"
  local f

  for f in \
    "${root}/subagent/Dockerfile" \
    "${root}/docker/subagent/Dockerfile" \
    "${root}/Dockerfile.subagent" \
    "${root}/Dockerfile"
  do
    [[ -f "${f}" ]] && { echo "${f}"; return; }
  done

  f="$(find "${root}" -maxdepth 5 -type f -name 'Dockerfile' | head -n 1 || true)"
  [[ -n "${f}" ]] || die "Dockerfile not found under ${root}"
  echo "${f}"
}

write_env_file() {
  cat > "${INSTALL_ROOT}/run/.env" <<EOF
TZ=${TZ_NAME}
CHASSISCLAW_AGENT_ID=${AGENT_ID}
SUBAGENT_PORT=${LISTEN_PORT}
CHASSISCLAW_CORE_URL=${CORE_URL}
EOF
}

write_compose_file() {
  local dockerfile_path="$1"
  local build_context
  local dockerfile_rel

  build_context="$(dirname "${dockerfile_path}")"
  dockerfile_rel="$(basename "${dockerfile_path}")"

  cat > "${INSTALL_ROOT}/run/compose.subagent.yml" <<EOF
services:
  subagent:
    container_name: ${SERVICE_NAME}
    build:
      context: ${build_context}
      dockerfile: ${dockerfile_rel}
    restart: unless-stopped
    network_mode: host
    environment:
      TZ: \${TZ}
      CHASSISCLAW_AGENT_ID: \${CHASSISCLAW_AGENT_ID}
      SUBAGENT_PORT: \${SUBAGENT_PORT}
      CHASSISCLAW_CORE_URL: \${CHASSISCLAW_CORE_URL}
    command: uvicorn app.main:app --host ${BIND_HOST} --port \${SUBAGENT_PORT}
EOF
}

start_subagent() {
  log "building and starting subagent"
  docker compose \
    --env-file "${INSTALL_ROOT}/run/.env" \
    -f "${INSTALL_ROOT}/run/compose.subagent.yml" \
    up -d --build
}

probe_health() {
  local url="http://127.0.0.1:${LISTEN_PORT}/health"
  local i

  log "probing health: ${url}"
  for i in $(seq 1 30); do
    if curl -fsS "${url}" >/dev/null 2>&1; then
      log "subagent is healthy"
      curl -fsS "${url}" || true
      echo
      return 0
    fi
    sleep 2
  done

  warn "health check failed"
  docker logs "${SERVICE_NAME}" --tail 100 || true
  return 1
}

main() {
  ensure_prereqs
  prepare_dirs

  if [[ -n "${BUNDLE_URL}" ]]; then
    fetch_source_bundle
  else
    fetch_source_repo
  fi

  local source_root
  local dockerfile_path

  source_root="$(detect_source_root)"
  dockerfile_path="$(detect_dockerfile "${source_root}")"

  log "source root: ${source_root}"
  log "dockerfile: ${dockerfile_path}"

  write_env_file
  write_compose_file "${dockerfile_path}"
  start_subagent
  probe_health

  log "done"
  log "local health: http://127.0.0.1:${LISTEN_PORT}/health"
}

main "$@"
