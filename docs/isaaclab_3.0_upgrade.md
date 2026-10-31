# Isaac Lab 3.0 upgrade — 2026-10-31

The project now uses the official `nvcr.io/nvidia/isaac-lab:3.0.0` container,
pinned by digest `sha256:f70acc9ed3bc3fc67099a0c5715379c432cc9965623cabbaf54f74599997e245`.
This image bundles Isaac Sim 6.2. It uses Python 3.12, PyTorch 2.11.0+cu130,
Warp 1.17, and RSL-RL 5.5.1. The RTX 5070 Ti was detected as CUDA device 0
with compute capability 12.0. The host NVIDIA driver remains 595.99.02.

The launcher uses the image's `/opt/isaaclab-venv` through its `isaaclab.sh`
wrapper and persists caches under `/home/yuto/docker/isaac-lab-3.0`. The standalone
Isaac Sim 6.2 GUI still has its own image and cache. Both mount this project at
`/workspace/so101`.

The SO-101 reaching task now declares its robot in `InteractiveSceneCfg`, lets
the scene clone environments, reads tensor data through `.torch`, and commands
joints through `actuators.target_command`. The asset validator uses the same
3.0 APIs. The registered task ID remains `SO101-Reach-Direct-v0`.

## Validation

All checks passed on the RTX 5070 Ti:

| Check | Result |
| --- | --- |
| Cartpole runtime | 8 environments, 240 steps, finite observations and rewards, seeded reset |
| SO-101 robot asset | 1 and 8 environments, all 6 joints mapped, shoulder and gripper motion, reset repeatability |
| SO-101 reaching task | 1 environment for 8 steps; 8 environments for 120 steps; finite observations and rewards, bounded actions and reset |
| RSL-RL training | 2 Cartpole iterations; `model_0.pt` and `model_1.pt` saved |

The 8-environment asset check measured at least 0.0432 rad of shoulder motion
and 0.1492 rad of gripper motion. The 8-environment reaching check saw a minimum
target distance of 0.1033 m. These checks establish that the environment runs;
they do not establish a trained reaching policy or task success rate.

```bash
cd /home/yuto/Robotics/Sim2Real_SO101_IsaacSim
./scripts/isaac-lab.sh pull
./scripts/isaac-lab.sh check
./scripts/isaac-lab.sh python /workspace/so101/scripts/validate_so101_lab_asset.py --num_envs 8
./scripts/isaac-lab.sh python /workspace/so101/scripts/validate_so101_reach_env.py --num_envs 8 --steps 120
./scripts/isaac-lab.sh ppo-check
```

JSON reports and console logs are under `logs/`. Training checkpoints are under
`outputs/isaaclab/training/rsl_rl/cartpole_direct/`. Both directories are ignored
by Git. Earlier training outputs and validation reports were retained.

The Isaac Sim 5.1 and Isaac Lab 2.3 images, stopped 5.1 container, 5.1 cache
directory, and fallback launcher were removed after these checks passed. Old
published validation documents remain as historical records.

References: [Isaac Lab 3.0 installation](https://isaac-sim.github.io/IsaacLab/v3.0.0/source/isaaclab/installation.html),
[3.0 migration guide](https://isaac-sim.github.io/IsaacLab/v3.0.0/source/isaaclab/migrating.html),
[Isaac Sim compatibility table](https://docs.isaacsim.omniverse.nvidia.com/6.2.0/installation/compatibility.html).
