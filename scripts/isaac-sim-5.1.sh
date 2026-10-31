#!/usr/bin/env bash
# Local Isaac Sim 5.1 Docker environment. Run from any directory.
set -euo pipefail
SCRIPT=$(realpath "${BASH_SOURCE[0]}")
PROJECT=$(dirname "$(dirname "$SCRIPT")")
IMAGE=nvcr.io/nvidia/isaac-sim:5.1.0
CACHE=/home/yuto/docker/isaac-sim-5.1
NAME=so101-isaac-sim
MODE=${1:-start}
if (($#)); then shift; fi
if [[ $MODE == help || $MODE == --help ]]; then
    echo "Usage: $SCRIPT {start [Kit arguments]|stop|status|logs|check|python SCRIPT [args]|shell}"
    exit 0
fi
# A desktop opened before usermod may have stale supplementary groups.
if ! id -nG | tr ' ' '\n' | grep -qx docker && id -nG "$(id -un)" | tr ' ' '\n' | grep -qx docker; then
    printf -v COMMAND ' %q' "$SCRIPT" "$MODE" "$@"
    exec sg docker -c "exec bash$COMMAND"
fi
docker info >/dev/null
case "$MODE" in
    stop) exec docker stop --timeout 30 "$NAME" ;;
    status) exec docker ps -a --filter "name=^/${NAME}$" ;;
    logs) exec docker logs --tail 100 -f "$NAME" ;;
    start|check|python|shell) ;;
    *) echo "Unknown mode: $MODE" >&2; exit 2 ;;
esac
# Keep the image's UID for its home/cache, but write project files with the host GID.
ARGS=(--runtime=nvidia --gpus all --init --shm-size=2g
    --user "1234:$(stat -c %g "$PROJECT")" --group-add "$(stat -c %g "$PROJECT/assets")"
    -e ACCEPT_EULA=Y -e NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics,display
    --mount "type=bind,src=$PROJECT,dst=/workspace/so101"
    --mount "type=bind,src=$CACHE/cache/main,dst=/isaac-sim/.cache"
    --mount "type=bind,src=$CACHE/cache/computecache,dst=/isaac-sim/.nv/ComputeCache"
    --mount "type=bind,src=$CACHE/logs,dst=/isaac-sim/.nvidia-omniverse/logs"
    --mount "type=bind,src=$CACHE/config,dst=/isaac-sim/.nvidia-omniverse/config"
    --mount "type=bind,src=$CACHE/data,dst=/isaac-sim/.local/share/ov/data"
    --mount "type=bind,src=$CACHE/pkg,dst=/isaac-sim/.local/share/ov/pkg"
    --entrypoint bash)
case "$MODE" in
    start)
        if [[ $(docker inspect -f '{{.State.Running}}' "$NAME" 2>/dev/null || true) == true ]]; then
            echo "Isaac Sim is already running: $NAME"; exit 0
        fi
        if docker container inspect "$NAME" >/dev/null 2>&1; then
            docker rm "$NAME" >/dev/null
        fi
        : "${DISPLAY:?Run start from your Ubuntu desktop session}"
        xdpyinfo -display "$DISPLAY" >/dev/null
        AUTH_DIR="${XDG_RUNTIME_DIR:-/tmp/so101-$(id -u)}/so101-isaac-sim"
        mkdir -p "$AUTH_DIR"
        chmod 700 "$AUTH_DIR"
        AUTH="$AUTH_DIR/Xauthority"
        touch "$AUTH"
        chmod 600 "$AUTH"
        # FamilyWild allows the same cookie inside a different container hostname.
        RECORDS=$(xauth nlist "$DISPLAY")
        [[ -n "$RECORDS" ]] || { echo "No X11 authorization found for $DISPLAY" >&2; exit 1; }
        printf '%s\n' "$RECORDS" | sed 's/^..../ffff/' | xauth -f "$AUTH" nmerge -
        chmod 640 "$AUTH"
        ARGS+=(-e DISPLAY -e XAUTHORITY=/tmp/isaac.xauth
            --mount "type=bind,src=$AUTH,dst=/tmp/isaac.xauth,readonly"
            --mount type=bind,src=/tmp/.X11-unix,dst=/tmp/.X11-unix,readonly)
        docker run -d --name "$NAME" "${ARGS[@]}" "$IMAGE" -c \
            'umask 002; exec ./runapp.sh --no-ros-env --/isaac/startup/ros_bridge_extension= --/app/window/width=1280 --/app/window/height=720 --/rtx/multiGpu/enabled=false "$@"' bash "$@"
        echo "Project: /workspace/so101"
        echo "Logs: $SCRIPT logs"
        ;;
    check)
        docker run --rm "${ARGS[@]}" "$IMAGE" -c \
            'umask 002; exec ./isaac-sim.compatibility_check.sh --no-ros-env --no-window --/app/quitAfter=10 "$@"' bash "$@"
        ;;
    python)
        (($#)) || { echo 'Supply a script path inside /workspace/so101.' >&2; exit 2; }
        docker run --rm "${ARGS[@]}" "$IMAGE" -c 'umask 002; exec ./python.sh "$@"' bash "$@"
        ;;
    shell)
        docker run --rm -it "${ARGS[@]}" "$IMAGE" -c 'umask 002; exec bash'
        ;;
esac
