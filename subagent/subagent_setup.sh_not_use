#!/usr/bin/env bash
set -euo pipefail

# =========================================================
# OpsClaw SubAgent setup (minimal, user-home install)
# - Pull ONLY subagent directory using git sparse-checkout
# - Install into $HOME/opsclaw (NOT /root)
# - If existing subagent stack/container exists -> down/cleanup
# - Bring up only subagent container
# - Run basic tests: /health, /a2a/run_script
#
# Usage:
#   bash subagent/subagent_setup.sh
#
# Optional env:
#   REPO_URL="https://github.com/mrgrit/opsclaw"
#   REPO_DIR="$HOME/opsclaw"
#   SUBAGENT_PORT="55123"
# =========================================================

REPO_URL="${REPO_URL:-https://github.com/mrgrit/opsclaw}"
SUBAGENT_PORT="${SUBAGENT_PORT:-55123}"

# IMPORTANT: lock install dir to the invoking user's HOME (not /root)
ORIG_USER="${SUDO_USER:-$USER}"
ORIG_HOME="$(getent passwd "$ORIG_USER" | cut -d: -f6)"
REPO_DIR="${REPO_DIR:-$ORIG_HOME/opsclaw}"

SUB_DIR="$REPO_DIR/subagent"
COMPOSE_FILE="$SUB_DIR/compose.subagent.yml"
STACK_NAME="opsclaw-subagent"
CONTAINER_NAME="opsclaw-subagent"

log()  { echo -e "\n\033[1;36m[opsclaw]\033[0m $*"; }
warn() { echo -e "\033[1;33m[warn]\033[0m $*"; }
die()  { echo -e "\n\033[1;31m[fail]\033[0m $*"; exit 1; }

need_cmd() { command -v "$1" >/dev/null 2>&1 || die "missing command: $1"; }

ensure_git() {
  if ! command -v git >/dev/null 2>&1; then
    warn "git not found. installing..."
    if command -v apt-get >/dev/null 2>&1; then
      sudo apt-get update -y
      sudo apt-get install -y git ca-certificates curl
    else
      die "no apt-get. install git manually."
    fi
  fi
}

ensure_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    warn "docker not found. installing docker.io + compose plugin..."
    if command -v apt-get >/dev/null 2>&1; then
      sudo apt-get update -y
      sudo apt-get install -y docker.io docker-compose-plugin
      sudo systemctl enable --now docker || true
    else
      die "no apt-get. install docker manually."
    fi
  fi

  # compose v2 check
  if ! docker compose version >/dev/null 2>&1; then
    die "docker compose plugin not available. install docker-compose-plugin."
  fi
}

sparse_checkout_subagent() {
  log "Install dir: $REPO_DIR (user=$ORIG_USER home=$ORIG_HOME)"
  mkdir -p "$REPO_DIR"

  if [ ! -d "$REPO_DIR/.git" ]; then
    log "Cloning repo (sparse) -> only subagent/"
    git clone --filter=blob:none --no-checkout "$REPO_URL" "$REPO_DIR"
    ( cd "$REPO_DIR"
      git sparse-checkout init --cone
      git sparse-checkout set subagent
      git checkout -f
    )
  else
    log "Repo exists. updating sparse checkout (subagent only)"
    ( cd "$REPO_DIR"
      git sparse-checkout init --cone >/dev/null 2>&1 || true
      git sparse-checkout set subagent
      git fetch --all --prune
      git pull --ff-only || true
    )
  fi

  [ -d "$SUB_DIR" ] || die "subagent directory not found after checkout: $SUB_DIR"
}

write_compose_if_missing() {
  mkdir -p "$SUB_DIR"

  if [ ! -f "$COMPOSE_FILE" ]; then
    log "Writing minimal compose: $COMPOSE_FILE"
    cat >"$COMPOSE_FILE" <<YAML
name: $STACK_NAME
services:
  subagent:
    container_name: $CONTAINER_NAME
    build:
      context: $SUB_DIR
      dockerfile: Dockerfile
    restart: unless-stopped
    ports:
      - "0.0.0.0:${SUBAGENT_PORT}:55123"
    environment:
      - TZ=Asia/Seoul
    volumes:
      - subagent_data:/data
volumes:
  subagent_data:
YAML
  else
    log "Compose exists: $COMPOSE_FILE"
  fi
}

cleanup_existing() {
  log "Cleanup existing subagent if any"

  # 1) If our compose stack exists, bring it down cleanly
  if docker compose -f "$COMPOSE_FILE" ps >/dev/null 2>&1; then
    docker compose -f "$COMPOSE_FILE" down || true
  fi

  # 2) If container with same name exists (from old runs), remove it
  if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
    warn "Removing existing container: $CONTAINER_NAME"
    docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
  fi
}

up_subagent() {
  log "Build & up subagent only"
  docker compose -f "$COMPOSE_FILE" build --no-cache subagent
  docker compose -f "$COMPOSE_FILE" up -d subagent
  docker compose -f "$COMPOSE_FILE" ps
}

wait_http_ok() {
  local url="$1"
  local tries=30
  local i=1
  while [ $i -le $tries ]; do
    if curl -sS --max-time 2 "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
    i=$((i+1))
  done
  return 1
}

basic_tests() {
  log "Basic tests"
  local base="http://127.0.0.1:${SUBAGENT_PORT}"

  if ! wait_http_ok "$base/health"; then
    docker compose -f "$COMPOSE_FILE" logs --tail=200 subagent || true
    die "health check failed: $base/health"
  fi

  log "health ok -> $base/health"
  curl -sS "$base/health" | sed 's/^/[health] /'

  log "run_script test -> uname -a"
  curl -sS -X POST "$base/a2a/run_script" \
    -H 'content-type: application/json' \
    -d "{\"run_id\":\"t1\",\"target_id\":\"local-agent-1\",\"script\":\"uname -a\",\"timeout_s\":20,\"approval_required\":false,\"evidence_requests\":[]}" \
    | sed 's/^/[run_script] /'

  log "DONE ✅  SubAgent is running on :$SUBAGENT_PORT"
}

main() {
  need_cmd curl
  ensure_git
  ensure_docker
  sparse_checkout_subagent
  write_compose_if_missing
  cleanup_existing
  up_subagent
  basic_tests

  log "Next: open port $SUBAGENT_PORT on firewall if remote access needed."
}

main "$@"