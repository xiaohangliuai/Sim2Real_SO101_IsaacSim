#!/usr/bin/env bash
# Isaac Lab 3.0.0 environment with its bundled Isaac Sim 6.2.
set -euo pipefail

SCRIPT=$(realpath "${BASH_SOURCE[0]}")
PROJECT=$(dirname "$(dirname "$SCRIPT")")
IMAGE_DIGEST=sha256:f70acc9ed3bc3fc67099a0c5715379c432cc9965623cabbaf54f74599997e245
IMAGE=nvcr.io/nvidia/isaac-lab@${IMAGE_DIGEST}
CACHE=/home/yuto/docker/isaac-lab-3.0
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
    mkdir -p "$CACHE"/{cache/kit,cache/ov,cache/pip,cache/glcache,cache/computecache,logs,data,documents}
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
    -e ACCEPT_EULA=Y
    -e NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics
    --mount "type=bind,src=$PROJECT,dst=/workspace/so101"
    --mount "type=bind,src=$PROJECT/outputs/isaaclab/training,dst=/workspace/isaaclab/logs"
    --mount "type=bind,src=$PROJECT/outputs/isaaclab/hydra,dst=/workspace/isaaclab/outputs"
    --mount "type=bind,src=$CACHE/cache/kit,dst=/isaac-sim/kit/cache"
    --mount "type=bind,src=$CACHE/cache/ov,dst=/root/.cache/ov"
    --mount "type=bind,src=$CACHE/cache/pip,dst=/root/.cache/pip"
    --mount "type=bind,src=$CACHE/cache/glcache,dst=/root/.cache/nvidia/GLCache"
    --mount "type=bind,src=$CACHE/cache/computecache,dst=/root/.nv/ComputeCache"
    --mount "type=bind,src=$CACHE/logs,dst=/root/.nvidia-omniverse/logs"
    --mount "type=bind,src=$CACHE/data,dst=/root/.local/share/ov/data"
    --mount "type=bind,src=$CACHE/documents,dst=/root/Documents"
    --entrypoint bash)

case "$MODE" in
    check)
        docker run --rm "${ARGS[@]}" "$IMAGE" -c \
            'umask 002; cd /workspace/isaaclab; exec ./isaaclab.sh -p /workspace/so101/scripts/validate_isaaclab_setup.py "$@"' bash "$@"
        ;;
    ppo-check)
        docker run --rm "${ARGS[@]}" "$IMAGE" -c \
            'umask 002; cd /workspace/isaaclab; exec ./isaaclab.sh -p scripts/reinforcement_learning/train.py --rl_library rsl_rl --task Isaac-Cartpole-Direct --num_envs 8 --max_iterations 2 --seed 42 --viz none presets=isaacsim_physx "$@"' bash "$@"
        ;;
    python)
        (($#)) || { echo 'Supply a script path inside /workspace/so101.' >&2; exit 2; }
        docker run --rm "${ARGS[@]}" "$IMAGE" -c \
            'umask 002; cd /workspace/isaaclab; exec ./isaaclab.sh -p "$@"' bash "$@"
        ;;
    shell)
        docker run --rm -it "${ARGS[@]}" "$IMAGE" -c \
            'umask 002; cd /workspace/so101; exec bash'
        ;;
esac
