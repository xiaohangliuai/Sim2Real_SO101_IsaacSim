# Isaac Lab runtime validation

The project uses NVIDIA's headless Isaac Lab 2.3.0 container on the existing
Isaac Sim 5.1 host. `scripts/isaac-lab.sh` pins this image digest:

```text
nvcr.io/nvidia/isaac-lab@sha256:1b204053c9facaa168b9aacd014061b479dabc0569f35f626dd60ea9d667188a
```

The [official Isaac Lab compatibility table](https://github.com/isaac-sim/IsaacLab)
lists the 2.3.x release family for Isaac Sim 5.1. The launcher reuses the Isaac
Sim caches and gives Isaac Lab separate writable Kit, Hydra, and training
directories. The training outputs remain under `outputs/isaaclab/`, which Git
ignores.

## Commands

Close the Isaac Sim GUI before running a headless check. From the project root:

```bash
./scripts/isaac-lab.sh pull
./scripts/isaac-lab.sh check
./scripts/isaac-lab.sh ppo-check
```

`pull` downloads the pinned image and creates the writable Kit cache. `check`
launches the official `Isaac-Cartpole-v0` task on `cuda:0` with eight parallel
environments, runs 240 steps, performs an additional seeded reset, checks tensor
shapes and finite observations/rewards, and records GPU memory use. The JSON
report is `logs/isaaclab_setup_validation.json`.

`ppo-check` launches the official RSL-RL Cartpole trainer with eight
environments, seed 42, and two learning iterations. It exercises rollout,
Actor/Critic optimization, logging, and checkpoint creation. Checkpoints and
Hydra metadata are stored under `outputs/isaaclab/`.

To run another script in the pinned runtime:

```bash
./scripts/isaac-lab.sh python /workspace/so101/path/to/script.py
```

## Measured result

| Measurement | Result |
|---|---:|
| Parallel environments | 8 |
| Steps per environment | 240 |
| Total environment steps | 1,920 |
| Policy observation shape | `(8, 4)` |
| Action shape | `(8, 1)` |
| Reward shape | `(8,)` |
| Explicit seeded resets | 1 |
| Throughput | 1,020.9 environment steps/s |
| Device-level peak GPU use | 3,491.1 MiB |
| Total GPU memory visible to PyTorch | 9,868.9 MiB |
| PPO iterations / timesteps | 2 / 256 |
| PPO checkpoints | `model_0.pt`, `model_1.pt` |

The device-level value includes Kit and other GPU allocations visible to CUDA;
the PyTorch allocator alone reserved 22 MiB at its peak. The measured headroom
was approximately 6,378 MiB. Memory use and throughput can change with other
GPU processes or a different task.

Validated Python packages in the pinned image:

| Package | Version |
|---|---:|
| Isaac Lab core | 0.47.1 |
| Isaac Lab tasks | 0.11.5 |
| PyTorch | 2.7.0+cu128 |
| RSL-RL | 3.0.1 |

These results verify the Isaac Lab installation and a small training workflow.
They do not demonstrate an SO-101 learning task or a trained pick-and-place
policy; those are separate development features.
