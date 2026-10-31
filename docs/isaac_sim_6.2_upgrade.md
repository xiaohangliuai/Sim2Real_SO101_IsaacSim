# Isaac Sim 6.2 upgrade — 2026-10-31

Upgraded the standalone Isaac Sim Docker launcher from 5.1.0 to 6.2.0 for
the NVIDIA GeForce RTX 5070 Ti. The existing host driver worked without changes.

## Installed environment

| Component | Version / configuration |
| --- | --- |
| Host | Ubuntu 24.04.5 LTS, Intel i5-13600K, 62 GiB RAM |
| GPU | NVIDIA GeForce RTX 5070 Ti, 16,303 MiB VRAM, compute capability 12.0 |
| Host NVIDIA driver | 595.99.02 |
| Docker / NVIDIA Container Toolkit | 29.8.1 / 1.20.1-1 |
| Image | `nvcr.io/nvidia/isaac-sim:6.2.0` |
| Image digest | `sha256:a025b65a7442d56806a1cc3f5eed081caf736c24b72d62dccf68ef66945d8690` |
| Bundled PyTorch / CUDA runtime | 2.11.0+cu128 / 12.8 |
| GUI container | `so101-isaac-sim-6.2` |
| Persistent cache and configuration | `/home/yuto/docker/isaac-sim-6.2` |

The image's internal VERSION string is
`6.2.0-rc.14+release.52805.02189a84.gl`, as shipped under NVIDIA's official
6.2.0 tag. The application experience identifies itself as 6.2.0.

## Validation

All headless commands exited with status 0:

| Check | Result |
| --- | --- |
| NVIDIA compatibility checker | PASSED; GPU and driver supported; VRAM good |
| CUDA kernel execution | 128×128 matrix multiplication passed on the GPU |
| Rendered physics smoke test | 120 steps passed; cube settled at z = 0.04999999 m |
| SO-101 composed scene | Passed; cube settled at z = 0.77000004 m; robot mount fixed |
| Articulation control | All six joints passed movement, return, and fixed-base checks |
| Full pick-and-place | 3/3 cycles passed; maximum final XY error 5.79 mm |
| Desktop GUI | Window opened; `Isaac Sim Full App is loaded` and `app ready`; container healthy |

Commands used:

```bash
./scripts/isaac-sim.sh check
./scripts/isaac-sim.sh python /workspace/so101/scripts/smoke_test.py
./scripts/isaac-sim.sh python /workspace/so101/scripts/validate_pick_place_scene.py
./scripts/isaac-sim.sh python /workspace/so101/scripts/validate_so101_articulation.py
./scripts/isaac-sim.sh python /workspace/so101/scripts/validate_so101_pick_place.py 3
```

Full logs, JSON reports, the generated 6.2 smoke-test USD, and pre-upgrade
README/launcher/scene/report backups are under `logs/upgrade-2026-10-31/`.
The original tracked smoke-test scene was restored after testing.
The GUI was left running on the desktop. Its first launch took about 130 seconds,
including roughly 90 seconds of RTX shader compilation into the new cache.

Three task cycles are an upgrade smoke test, not a replacement for the project's
full 20-cycle validation or a training benchmark. The project's existing Core
and Lula APIs still work in these checks but are deprecated in Isaac Sim 6.x.
Headless startup emits no-display warnings; startup also warns that the optional
OmniHub cache service is absent. These did not prevent the checks from passing.
The compatibility checker recommends a performance CPU governor; the existing
powersave setting was retained.
The GUI also logged bundled Fabric interface-version and initial material-cache
warnings; it subsequently reached readiness and passed its container health check.

## Launch and rollback

```bash
cd /home/yuto/Robotics/Sim2Real_SO101_IsaacSim
./scripts/isaac-sim.sh start
./scripts/isaac-sim.sh status
./scripts/isaac-sim.sh stop
```

To use the retained 5.1 installation after stopping 6.2:

```bash
./scripts/isaac-sim-5.1.sh start
# Later:
./scripts/isaac-sim-5.1.sh stop
```

The old image, stopped container `so101-isaac-sim`, and
`/home/yuto/docker/isaac-sim-5.1` caches remain available. Both launchers mount
the same project at `/workspace/so101`; save scenes there. The new `pull` command
downloads 6.2 and prepares its cache permissions if setup must be repeated.

`scripts/isaac-lab.sh` remains pinned to Isaac Lab 2.3.0 with its own Isaac Sim
5.1 runtime. This upgrade did not migrate or revalidate Isaac Lab or run training.

## NVIDIA references

- [Container installation](https://docs.isaacsim.omniverse.nvidia.com/latest/installation/install_container.html)
- [System requirements](https://docs.isaacsim.omniverse.nvidia.com/latest/installation/requirements.html)
- [Core API migration guide](https://docs.isaacsim.omniverse.nvidia.com/latest/migration_guides/isaac_sim_6_0/core_api_to_core_experimental.html)
