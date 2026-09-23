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
./scripts/isaac-sim.sh python /workspace/so101/scripts/validate_so101_articulation.py
./scripts/isaac-sim.sh python /workspace/so101/scripts/validate_pick_place_reset.py
./scripts/isaac-sim.sh python /workspace/so101/scripts/validate_so101_reach.py
./scripts/isaac-sim.sh python /workspace/so101/scripts/validate_so101_grasp.py
./scripts/isaac-sim.sh python /workspace/so101/scripts/validate_so101_pick_place.py
```

This check opens `scenes/so101_pick_place_task.usda`, verifies the robot
articulation, cube collision setup, target material binding, and end-effector
frame, then runs 240 physics steps and confirms that the cube settles on the
table while the robot mount stays fixed. The result is written to
`logs/pick_place_scene_validation.json`.

The articulation check records the stable six-DOF controller ordering, limits,
drive properties, independent positive motion, return error, and fixed-base
drift. Its result is written to `logs/so101_articulation_validation.json`; the
validated ordering is documented in `docs/so101_joint_validation.md`.

The reset stress test deliberately perturbs the robot, cube, and target before
each of 20 resets. It verifies repeatable joint and object state, cleared
velocities, and a fixed robot mount. Its result is written to
`logs/pick_place_reset_validation.json`.

The reach check loads the five-axis Lula configuration and executes all six
pick-and-place waypoints with position-priority IK. Its measured endpoint errors
are recorded in `logs/so101_reach_validation.json` and summarized in
`docs/so101_reach_validation.md`.

The grasp check uses fixed-wrist position IK and a side-entry jaw alignment, then
runs 20 reset, grasp, lift, and hold trials. The task scene supplies explicit
finger collision proxies and a high-friction contact material. Per-trial results
are recorded in `logs/so101_grasp_validation.json` and summarized in
`docs/so101_grasp_validation.md`.

The complete pick-and-place check carries the grasped cube to the target,
places and releases it, retreats without disturbing it, and returns the robot
home. It runs 20 full cycles and records placement accuracy, settled velocity,
and home-position error in `logs/so101_pick_place_validation.json`. The
controller and measured results are documented in
`docs/so101_pick_place_validation.md`.

## Isaac Lab setup

The headless Isaac Lab runtime uses NVIDIA's Isaac Lab 2.3.0 image, pinned by
digest for the installed Isaac Sim 5.1 version. Close the Isaac Sim GUI, then
run these checks from the project root:

```bash
./scripts/isaac-lab.sh pull
./scripts/isaac-lab.sh check
./scripts/isaac-lab.sh ppo-check
```

`check` runs eight GPU Cartpole environments for 240 steps, including a second
seeded reset, and writes `logs/isaaclab_setup_validation.json`. `ppo-check`
runs two RSL-RL training iterations and saves checkpoints under the ignored
`outputs/isaaclab/` directory. These checks validate the Isaac Lab runtime;
the SO-101 Isaac Lab task is the next development stage. See
`docs/isaaclab_setup_validation.md` for measured results and limitations.

Validate the SO-101 robot asset in one and eight Isaac Lab environments:

```bash
./scripts/isaac-lab.sh python /workspace/so101/scripts/validate_so101_lab_asset.py --headless --num_envs 1
./scripts/isaac-lab.sh python /workspace/so101/scripts/validate_so101_lab_asset.py --headless --num_envs 8
```

This checks the six-joint mapping, movement, and reset using the imported robot
USD. Results and the current scope are documented in
`docs/so101_lab_asset_validation.md`.

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
roadmap; ROS and the SO-101 Isaac Lab task are later steps. First startup may take several
minutes while shaders compile.

Logs are in `logs/` for setup checks and
`/home/yuto/docker/isaac-sim-5.1/logs` for persistent application logs.
Headless checks can print GLFW/no-display warnings because they have no GUI.

Reference: [NVIDIA Isaac Sim 5.1 container documentation](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/installation/install_container.html#container-deployment-with-gui).
