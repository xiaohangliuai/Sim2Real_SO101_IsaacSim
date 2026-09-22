# SO-101 Isaac Sim environment

This project uses the installed `nvcr.io/nvidia/isaac-sim:5.1.0` Docker image.
The directory `/home/yuto/docker/isaac-sim-5.1` stores persistent caches, settings,
and logs; the application itself is inside the Docker image.

## Start and stop

Run from your Ubuntu desktop terminal:

```bash
cd /home/yuto/Robotics/Sim2Real_SO101_IsaacSim
./scripts/isaac-sim.sh start
./scripts/isaac-sim.sh status
./scripts/isaac-sim.sh logs
./scripts/isaac-sim.sh stop
```

`start` opens the GUI on the current desktop display and leaves Docker running
independently of the terminal. Closing the GUI stops the application. Running
`start` again recreates the stopped container and retains all mounted data.
Save work under `/workspace/so101` before stopping; changes elsewhere in the
container, including installed packages, are not retained when it is recreated.

The launcher handles a desktop session with stale Docker group membership using
`sg docker`; no password is needed when your account already belongs to that
group. Logging out and back in also makes ordinary `docker` commands available.
X11 uses a private authorization file in the session runtime directory.

## Project paths

| Host | Inside Isaac Sim |
| --- | --- |
| This project | `/workspace/so101` |
| `assets/robots/so101/so101_new_calib.urdf` | `/workspace/so101/assets/robots/so101/so101_new_calib.urdf` |
| `scenes` | `/workspace/so101/scenes` |
| `scripts` | `/workspace/so101/scripts` |

Use **File > Open** to open a USD scene. The URDF and adjacent mesh directory are
ready for the later robot-import phase in the roadmap.

## Verify or run Python

Close the GUI before running a second simulator instance on the 10 GB GPU.

```bash
./scripts/isaac-sim.sh check
./scripts/isaac-sim.sh python /workspace/so101/scripts/smoke_test.py
./scripts/isaac-sim.sh shell
```

The Python command uses Isaac Sim's bundled Python and packages. The smoke test
renders 120 physics steps, checks that a cube falls and settles on a local ground
primitive, and saves `scenes/environment_smoke_test.usd` plus
`logs/environment_smoke_test.json`. It does not require cloud scene assets.

Validate the composed SO-101 pick-and-place scene after closing the GUI:

```bash
./scripts/isaac-sim.sh python /workspace/so101/scripts/validate_pick_place_scene.py
```

This check opens `scenes/so101_pick_place_task.usda`, verifies the robot
articulation, cube collision setup, target material binding, and end-effector
frame, then runs 240 physics steps and confirms that the cube settles on the
table while the robot mount stays fixed. The result is written to
`logs/pick_place_scene_validation.json`.

The launcher uses the image's UID 1234 and the project owner's group for project
writes. It reuses the cache directories already owned by UID 1234. New project
files are group-writable. NVIDIA license acceptance is set for application
startup; optional telemetry consent is not enabled by this launcher.

## Versions and diagnostics

Verified host on 2026-09-19 UTC:

- GPU: NVIDIA GeForce RTX 3080, 10,240 MiB VRAM
- NVIDIA driver: 580.173.02
- Docker Engine: 29.8.1
- NVIDIA Container Toolkit: 1.20.1-1
- Image tag: `nvcr.io/nvidia/isaac-sim:5.1.0`
- Installed image digest: `sha256:f3563cb2ba0c18af0b2fb321360dcb73a917b899f879e3213623d6bee484fa54`
- Compatibility checker: PASSED; VRAM sufficient with more recommended
- Rendered physics smoke test: PASSED, cube settled at z = 0.0499998 m
- Project mount: USD scene and JSON report saved successfully
- CPU governor: powersave; checker recommends performance for heavier work

Start with small scenes and modest camera resolutions. The launcher opens a
1280x720 logical window with multi-GPU rendering disabled. Automatic ROS 2
bridge startup is disabled for this initial simulation phase, as planned in the
roadmap; ROS and Isaac Lab integration are later steps. First startup may take several
minutes while shaders compile.

Logs are in `logs/` for setup checks and
`/home/yuto/docker/isaac-sim-5.1/logs` for persistent application logs.
Headless checks can print GLFW/no-display warnings because they have no GUI.

Reference: [NVIDIA Isaac Sim 5.1 container documentation](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/installation/install_container.html#container-deployment-with-gui).
