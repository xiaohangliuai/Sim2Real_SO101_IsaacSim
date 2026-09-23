#!/usr/bin/env bash
# Reproducible headless Isaac Lab 2.3.0 environment for Isaac Sim 5.1.
set -euo pipefail

SCRIPT=$(realpath "${BASH_SOURCE[0]}")
PROJECT=$(dirname "$(dirname "$SCRIPT")")
IMAGE_DIGEST=sha256:1b204053c9facaa168b9aacd014061b479dabc0569f35f626dd60ea9d667188a
IMAGE=nvcr.io/nvidia/isaac-lab@${IMAGE_DIGEST}
CACHE=/home/yuto/docker/isaac-sim-5.1
MODE=${1:-check}
if (($#)); then shift; fi

if [[ $MODE == help || $MODE == --help ]]; then
    echo "Usage: $SCRIPT {pull|check [args]|ppo-check [args]|python SCRIPT [args]|shell}"
    exit 0
fi

if ! id -nG | tr ' ' '\n' | grep -qx docker && id -nG "$(id -un)" | tr ' ' '\n' | grep -qx docker; then
    printf -v COMMAND ' %q' "$SCRIPT" "$MODE" "$@"
    exec sg docker -c "exec bash$COMMAND"
fi

docker info >/dev/null

if [[ $MODE == pull ]]; then
    docker pull "$IMAGE"
    docker image inspect "$IMAGE" >/dev/null
    docker run --rm --entrypoint bash \
        --mount "type=bind,src=$CACHE/cache,dst=/cache" \
        "$IMAGE" -c \
        'mkdir -p /cache/kit && chown 1234:1234 /cache/kit && chmod 775 /cache/kit'
    echo "Verified Isaac Lab image: $IMAGE"
    exit 0
fi

case "$MODE" in
    check|ppo-check|python|shell) ;;
    *) echo "Unknown mode: $MODE" >&2; exit 2 ;;
esac

docker image inspect "$IMAGE" >/dev/null 2>&1 || {
    echo "Missing image. Run: $SCRIPT pull" >&2
    exit 1
}
[[ -d $CACHE/cache/kit ]] || {
    echo "Missing writable Kit cache. Run: $SCRIPT pull" >&2
    exit 1
}

mkdir -p "$PROJECT/outputs/isaaclab/training" "$PROJECT/outputs/isaaclab/hydra"

ARGS=(--runtime=nvidia --gpus all --init --shm-size=4g
    --user "1234:$(stat -c %g "$PROJECT")"
    --group-add "$(stat -c %g "$PROJECT/assets")"
    -e ACCEPT_EULA=Y -e HOME=/isaac-sim
    -e NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics
    --mount "type=bind,src=$PROJECT,dst=/workspace/so101"
    --mount "type=bind,src=$PROJECT/outputs/isaaclab/training,dst=/workspace/isaaclab/logs"
    --mount "type=bind,src=$PROJECT/outputs/isaaclab/hydra,dst=/workspace/isaaclab/outputs"
    --mount "type=bind,src=$CACHE/cache/kit,dst=/isaac-sim/kit/cache"
    --mount "type=bind,src=$CACHE/cache/main,dst=/isaac-sim/.cache"
    --mount "type=bind,src=$CACHE/cache/computecache,dst=/isaac-sim/.nv/ComputeCache"
    --mount "type=bind,src=$CACHE/logs,dst=/isaac-sim/.nvidia-omniverse/logs"
    --mount "type=bind,src=$CACHE/config,dst=/isaac-sim/.nvidia-omniverse/config"
    --mount "type=bind,src=$CACHE/data,dst=/isaac-sim/.local/share/ov/data"
    --mount "type=bind,src=$CACHE/pkg,dst=/isaac-sim/.local/share/ov/pkg"
    --entrypoint bash)

case "$MODE" in
    check)
        docker run --rm "${ARGS[@]}" "$IMAGE" -c \
            'umask 002; exec /isaac-sim/python.sh /workspace/so101/scripts/validate_isaaclab_setup.py --headless "$@"' bash "$@"
        ;;
    ppo-check)
        docker run --rm "${ARGS[@]}" "$IMAGE" -c \
            'umask 002; exec /isaac-sim/python.sh /workspace/isaaclab/scripts/reinforcement_learning/rsl_rl/train.py --task Isaac-Cartpole-v0 --num_envs 8 --max_iterations 2 --seed 42 --headless --run_name so101_setup_smoke "$@"' bash "$@"
        ;;
    python)
        (($#)) || { echo 'Supply a script path inside /workspace/so101.' >&2; exit 2; }
        docker run --rm "${ARGS[@]}" "$IMAGE" -c \
            'umask 002; exec /isaac-sim/python.sh "$@"' bash "$@"
        ;;
    shell)
        docker run --rm -it "${ARGS[@]}" "$IMAGE" -c \
            'umask 002; cd /workspace/so101; exec bash'
        ;;
esac
