# SO-101 Isaac Sim Sim-to-Real Roadmap

## Project goal

Build an SO-101 simulation and training workflow from scratch with NVIDIA Isaac Sim and Isaac Lab, then transfer the trained behavior to the physical SO-101.

The first complete task will be:

```text
home -> approach cube -> grasp -> lift -> move to target -> release -> home
```

This project intentionally does **not** clone NVIDIA's complete SO-101 workshop repository. The workshop can be used as a reference, but the project structure, robot import, scene, task, training configuration, and deployment code will be built locally and understood one piece at a time.

---

## Current starting point

Completed:

- [x] Native Ubuntu 24.04 installed
- [x] NVIDIA GeForce RTX 3080 detected by Ubuntu
- [x] NVIDIA driver works on the host

Confirm the host GPU whenever necessary:

```bash
nvidia-smi
```

Do not install a second NVIDIA kernel driver inside a Docker container. The host owns the driver; containers use it through NVIDIA Container Toolkit.

Planned software path:

```text
Native Ubuntu 24.04
        |
        +-- NVIDIA host driver -> RTX 3080
        |
        +-- Docker Engine
                |
                +-- NVIDIA Container Toolkit
                        |
                        +-- Isaac Sim container
                                |
                                +-- SO-101 USD asset
                                +-- Isaac Lab task
                                +-- training and evaluation
```

The RTX 3080 has limited VRAM compared with the larger GPUs often used for Isaac Lab training. Begin with small environment counts and modest camera settings, monitor memory with `nvidia-smi`, and scale only after the basic task runs reliably.

---

# Phase 1 — Install and understand Docker

Docker runs software in isolated environments called **containers**.

- An **image** is a saved template containing an operating-system userspace, applications, and dependencies.
- A **container** is a running instance of an image.
- Docker does not replace Ubuntu and does not emulate the RTX 3080.
- NVIDIA Container Toolkit makes the host GPU available inside selected containers.

The immediate goal of this phase is only:

```text
docker run hello-world
```

## 1.1 Remove conflicting packages

It is fine if Ubuntu says that some of these packages are not installed.

```bash
sudo apt remove -y \
  docker.io \
  docker-compose \
  docker-compose-v2 \
  docker-doc \
  podman-docker \
  containerd \
  runc
```

## 1.2 Install the tools used to add Docker's repository

```bash
sudo apt update
sudo apt install -y ca-certificates curl
```

What these do:

- `apt update` refreshes Ubuntu's list of available packages; it does not upgrade the operating system.
- `ca-certificates` lets Ubuntu validate secure HTTPS sites.
- `curl` downloads files from the command line.
- `-y` automatically confirms the installation prompt.

## 1.3 Add Docker's signing key

```bash
sudo install -m 0755 -d /etc/apt/keyrings

sudo curl -fsSL \
  https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc

sudo chmod a+r /etc/apt/keyrings/docker.asc
```

The signing key lets Ubuntu verify that packages really came from Docker. The first command creates the key folder; the last command makes the key readable by the package manager.

## 1.4 Add Docker's official Ubuntu repository

```bash
sudo tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
```

On Ubuntu 24.04, the suite resolves to `noble`. On a standard Intel/AMD desktop, the architecture normally resolves to `amd64`.

Refresh the package list again so it includes the newly added Docker repository:

```bash
sudo apt update
```

## 1.5 Install Docker Engine

```bash
sudo apt install -y \
  docker-ce \
  docker-ce-cli \
  containerd.io \
  docker-buildx-plugin \
  docker-compose-plugin
```

The important pieces are:

| Package | Purpose |
|---|---|
| `docker-ce` | Docker Engine |
| `docker-ce-cli` | The `docker` command |
| `containerd.io` | Low-level container management |
| `docker-buildx-plugin` | Builds images |
| `docker-compose-plugin` | Runs multi-container configurations |

## 1.6 Verify Docker

```bash
sudo systemctl status docker
```

The service should report `active (running)`. Exit the status screen with `q`.

Then run:

```bash
sudo docker run hello-world
```

Expected milestone:

```text
Hello from Docker!
```

\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\09/18

## 1.7 Optional: use Docker without `sudo`

```bash
sudo groupadd docker 2>/dev/null || true
sudo usermod -aG docker "$USER"
newgrp docker
docker run hello-world
```

Membership in the `docker` group is effectively administrative access to the machine. Only add trusted local users.

Checkpoint:

- [ ] `docker --version` works
- [ ] Docker service is active
- [ ] `docker run hello-world` succeeds
- [ ] Docker works without `sudo`, if the optional group step was used

---

# Phase 2 — Give Docker access to the RTX 3080

Docker can run before it can use the GPU. NVIDIA Container Toolkit creates this path:

```text
Isaac Sim container -> NVIDIA container runtime -> host NVIDIA driver -> RTX 3080
```

## 2.1 Install prerequisites

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg2
```

## 2.2 Add NVIDIA's repository key

```bash
curl -fsSL \
  https://nvidia.github.io/libnvidia-container/gpgkey \
  | sudo gpg --dearmor \
  -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
```

## 2.3 Add the NVIDIA Container Toolkit repository

```bash
curl -s -L \
  https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update
```

## 2.4 Install and configure the toolkit

```bash
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

## 2.5 Test the GPU from inside a container

The image tag below is the one used in the conversation. If NVIDIA has retired that exact tag, choose a currently available CUDA Ubuntu 24.04 base image that is compatible with the installed host driver.

```bash
docker run --rm \
  --runtime=nvidia \
  --gpus all \
  nvcr.io/nvidia/cuda:12.8.0-base-ubuntu24.04 \
  nvidia-smi
```

Success means the output inside the container identifies the RTX 3080 and displays a driver/CUDA compatibility version.

Checkpoint:

- [ ] Host `nvidia-smi` sees the RTX 3080
- [ ] `nvidia-container-toolkit` is installed
- [ ] Docker was restarted after runtime configuration
- [ ] Container `nvidia-smi` sees the RTX 3080

Do not continue to Isaac Sim until this checkpoint passes.

---

# Phase 3 — Create the project from scratch

Use this project folder as the working root:

```bash
cd /home/yuto/Robotics/Sim2Real_SO101_IsaacSim

mkdir -p \
  assets/robots/so101 \
  assets/objects \
  scenes \
  scripts \
  configs \
  source/so101_tasks \
  data \
  logs \
  outputs
```

Target layout:

```text
Sim2Real_SO101_IsaacSim/
├── SO101_IsaacSim_Sim2Real_Roadmap.md
├── assets/
│   ├── robots/
│   │   └── so101/
│   └── objects/
├── scenes/
├── scripts/
├── configs/
├── source/
│   └── so101_tasks/
├── data/
├── logs/
└── outputs/
```

Keep source robot files separate from converted USD assets so the conversion is repeatable.

---

# Phase 4 — Obtain only the SO-101 robot description

Do not clone the full NVIDIA workshop repository.

Obtain the SO-101 URDF and all meshes it references from an authoritative SO-101 source. The conversation identified the SO-ARM project files, including a URDF such as:

```text
so101_new_calib.urdf
```

and its adjacent mesh folder:

```text
assets/*.stl
```

Preserve their relative layout because the URDF may contain paths like:

```xml
<mesh filename="assets/base_motor_holder_so101_v1.stl"/>
```

Expected local layout:

```text
assets/robots/so101/
├── source/
│   ├── so101_new_calib.urdf
│   └── assets/
│       ├── base_motor_holder_so101_v1.stl
│       ├── base_so101_v2.stl
│       ├── upper_arm_so101_v1.stl
│       ├── under_arm_so101_v1.stl
│       └── ...
└── usd/
```

Before importing, inspect and record:

- Joint names and ordering
- Joint axes and positive directions
- Joint lower and upper limits
- Zero pose and calibration convention
- Gripper joint behavior
- Mesh scale and units
- Collision meshes
- Link masses, centers of mass, and inertias

The simulation and real arm must eventually agree on joint order, sign, offset, units, and limits.

---

# Phase 5 — Run Isaac Sim in Docker

Use an official Isaac Sim container version that is compatible with the chosen Isaac Lab release and the installed host driver. Pin the exact working image tag in project notes rather than using an unversioned tag.

Before the first pull:

1. Create or sign in to an NVIDIA NGC account if the selected image requires it.
2. Accept the relevant NVIDIA container license/EULA.
3. Authenticate Docker to `nvcr.io` if required.
4. Confirm the version compatibility between Isaac Sim, Isaac Lab, Python, and the NVIDIA driver.

The eventual container needs:

- `--gpus all` for GPU access
- a bind mount for this project directory
- persistent cache mounts so shaders and packages are not rebuilt every run
- appropriate display or streaming configuration for the Isaac Sim UI
- acceptance of the NVIDIA EULA and privacy terms through the documented environment variables

Conceptual launch shape:

```bash
docker run --rm -it \
  --gpus all \
  --network host \
  -e ACCEPT_EULA=Y \
  -e PRIVACY_CONSENT=Y \
  -v /home/yuto/Robotics/Sim2Real_SO101_IsaacSim:/workspace/so101 \
  <official-isaac-sim-image:version>
```

This is a template, not yet the final GUI command. Display forwarding, cache paths, and the exact startup executable depend on the pinned Isaac Sim release. Follow that release's official container instructions when filling in the placeholders.

First Isaac Sim milestones:

- [ ] The container starts without GPU errors
- [ ] Isaac Sim reports the RTX 3080 renderer
- [ ] A blank stage opens or runs headlessly
- [ ] A cube can be created, simulated, and saved
- [ ] The project folder is visible inside the container at `/workspace/so101`

---

# Phase 6 — Import and validate the SO-101

Use Isaac Sim's URDF importer to convert the local SO-101 description into USD. Save the result in the project's `assets/robots/so101/usd/` folder.

Import checks:

- Use meters, not millimeters.
- Keep the base fixed for a tabletop robot.
- Import the arm as an articulation.
- Confirm each revolute joint axis.
- Confirm joint limits and zero positions.
- Inspect collision geometry separately from visual geometry.
- Verify link mass, center of mass, and inertia.
- Add or tune joint drives only after the kinematic model is correct.

Create a small validation script that commands one joint at a time:

```text
joint 1: 0 -> small positive angle -> 0
joint 2: 0 -> small positive angle -> 0
...
gripper: open -> close -> open
```

For every joint, record:

| Field | Value to verify |
|---|---|
| Joint name | Same in URDF, USD, task, and real API |
| Index | Stable controller ordering |
| Axis | Correct physical axis |
| Positive sign | Same direction as real robot |
| Zero | Same reference pose |
| Minimum/maximum | Safe real limits |
| Units | Radians internally |

Do not begin learning until this table is correct. A visually convincing robot with incorrect coordinate conventions will produce poor sim-to-real transfer.

Checkpoint:

- [ ] SO-101 appears at the correct size
- [ ] Base is fixed and stable
- [ ] Every joint moves independently as expected
- [ ] Gripper opens and closes correctly
- [ ] Joint names, order, axes, signs, and limits are documented
- [ ] The validated USD asset is saved locally

---

# Phase 7 — Build a minimal tabletop scene

Create one clean scene containing:

- A ground plane
- A table
- The fixed-base SO-101
- One cube
- One target area or container
- One camera placeholder
- Simple lighting

Start without photorealism. The first purpose of the scene is to validate physics and task logic.

Useful reset behavior:

- Arm returns to a known safe home pose.
- Gripper opens.
- Cube position is reset.
- Target position is reset.
- Velocities are cleared.
- The scene remains collision-free.

---

# Phase 8 — Install and validate Isaac Lab

Use an Isaac Lab release that explicitly supports the pinned Isaac Sim version. Do not mix arbitrary versions.

Before creating the custom task, run one official lightweight Isaac Lab example and verify:

- The app launches using the RTX 3080.
- A small number of parallel environments runs.
- Reset and simulation stepping work.
- Training dependencies load.
- VRAM use remains safe.

Begin with a low environment count, for example 8 or 16. Increase to 32, 64, or more only after observing stable VRAM and frame time. Vision environments use much more memory than state-only environments.

---

# Phase 9 — Define the first learning task

Begin with **state-based reinforcement learning**, not RGB vision.

At each simulation step, an **observation** is the information the policy receives. An **action** is what the policy commands. A **reward** measures progress. The policy learns this mapping:

```python
action = policy(observation)
```

## 9.1 Observation space

A first observation can contain:

```python
observation = [
    joint_positions,
    joint_velocities,
    cube_position,
    target_position,
]
```

Isaac Sim already knows the exact cube and target coordinates, so the first policy can use simulator state directly. This isolates robot control and reward design from camera perception.

A fuller state vector may include:

```python
obs = concat([
    joint_positions,       # arm and gripper
    joint_velocities,
    end_effector_position,
    end_effector_rotation,
    cube_position,
    cube_rotation,
    target_position,
    previous_action,
])
```

Normalize inputs and keep the ordering fixed.

## 9.2 Action space

Start with bounded joint-position targets or small joint-position increments:

```python
action = [
    shoulder_pan,
    shoulder_lift,
    elbow,
    wrist_pitch,
    wrist_roll,
    gripper,
]
```

Document exactly whether each value is an absolute target, an offset, a velocity, or a torque. Position targets are the safest and simplest starting point for this arm.

## 9.3 Curriculum

Train in this order:

1. Reach a fixed point.
2. Reach a randomly positioned cube.
3. Close the gripper around the cube.
4. Lift the cube.
5. Move the cube toward a target.
6. Release it inside the target.
7. Return home.

Do not debug the full pick-and-place sequence before the reaching task is reliable.

## 9.4 Reward progression

Reaching:

```text
reward = -distance(end_effector, cube)
```

Grasping and lifting:

```text
reward = reaching_progress
       + grasp_bonus
       + lift_progress
       - unsafe_motion_penalty
```

Pick-and-place:

```text
reward = reaching_progress
       + grasp_bonus
       + lift_progress
       + object_to_target_progress
       + success_bonus
       - action_penalty
       - collision_penalty
```

Add termination conditions for success, dropped objects, unsafe joint states, and timeouts.

PPO is a reasonable first algorithm because Isaac Lab can collect experience from many parallel environments.

---

# Phase 10 — Establish a nominal simulation baseline

Before randomization, train and evaluate a deterministic or lightly randomized task.

Record:

- Training seed and configuration
- Isaac Sim and Isaac Lab versions
- Robot USD version
- Number of parallel environments
- Training time and VRAM use
- Success definition
- Success rate over held-out episodes
- Common failure modes

Target a high, repeatable success rate in simulation before adding more complexity. Do not treat one successful video as evaluation.

---

# Phase 11 — Add domain randomization

Sim-to-real does not require one supposedly perfect simulation. Train across a distribution of plausible systems so the policy tolerates real-world differences.

Start with narrow, defensible ranges and widen them after measurement.

## Physics randomization

- Link mass and center-of-mass variation
- Joint damping and friction
- Actuator stiffness and damping/gains
- Motor strength variation
- Table and object friction
- Object mass
- Restitution
- Action delay and control-rate jitter

## Sensor and state randomization

- Joint position and velocity noise
- State latency
- Cube/target pose noise
- Dropped or delayed observations where realistic

## Scene and visual randomization

- Cube and target pose
- Camera translation and rotation
- Light intensity, direction, and color
- Materials, textures, and background
- Camera exposure and image noise
- Small object-size and color changes

Initial example ranges discussed in the conversation were approximately:

```text
motor strength:       ±10–20%
joint damping:        ±20–30%
camera position:      ±1–3 cm
camera rotation:      ±2–5 degrees
object position:      randomized in safe workspace
sensor noise:         small and measured where possible
action latency:       randomized around measured delay
```

These are starting ideas, not measured SO-101 specifications. Replace guesses with real measurements after the arm arrives.

Evaluation sets:

1. Nominal simulation
2. Training randomization distribution
3. Held-out randomization outside common training combinations
4. Real robot

---

# Phase 12 — Add cameras only after state-based control works

In state-based training, simulation provides the exact cube position. A physical robot cannot obtain that value without sensing.

Two later options are:

```text
camera image -> perception model -> estimated cube pose -> state policy
```

or:

```text
RGB image + joint state -> end-to-end vision policy -> robot action
```

Recommended progression:

1. Add an Isaac Sim camera matching the planned real camera viewpoint.
2. Match approximate resolution, field of view, pose, and frame rate.
3. Validate image capture independently.
4. Randomize camera pose, lighting, materials, and image characteristics.
5. Begin with a simple perception pipeline or an imitation policy.
6. Compare state-policy and vision-policy failures separately.

Starting with RGB too early makes it difficult to determine whether failures come from perception, physics, camera calibration, control, reward design, or the policy itself.

---

# Phase 13 — Optional imitation-learning path

After the basic Isaac Lab task is stable, simulated or real teleoperation demonstrations can support imitation learning.

Possible later path:

```text
SO-101 leader arm or simulated teleoperation
        |
        v
record demonstrations
        |
        v
LeRobot-compatible dataset
        |
        v
ACT / diffusion policy / VLA-style policy
        |
        v
optional RL fine-tuning
        |
        v
real SO-101 deployment
```

Do not install ROS, LeRobot, a VLA stack, or multiple RL frameworks during the initial Docker/GPU/asset-validation phases. Add each only when the prior milestone is working and version-controlled.

---

# Phase 14 — Calibrate the physical SO-101

When the arm arrives, do not deploy a learned policy immediately.

First create a calibration table for every joint:

| Joint | Sim zero | Real zero | Sign | Offset | Minimum | Maximum |
|---|---:|---:|---:|---:|---:|---:|
| Shoulder pan | | | | | | |
| Shoulder lift | | | | | | |
| Elbow | | | | | | |
| Wrist pitch | | | | | | |
| Wrist roll | | | | | | |
| Gripper | | | | | | |

Compare at least:

```text
simulation joint = 0     versus real joint = 0
simulation joint = +30°  versus real joint = +30°
```

for every joint, using safe motion ranges.

The sim and real interfaces must agree on:

- Joint ordering
- Sign/direction
- Zero offsets
- Units
- Safe limits
- Position-command convention
- Gripper open/closed convention

---

# Phase 15 — Characterize real actuators and latency

Measure the actual arm instead of assuming ideal simulation drives.

For several safe step commands, such as 0° to 15° and 0° to 30°, record:

- Response delay
- Rise time
- Overshoot
- Settling time
- Steady-state error
- Maximum observed velocity
- Repeatability
- Effects of payload and direction

Then tune nominal actuator behavior and randomization ranges in simulation. Measure the end-to-end loop delay from sensing through policy inference to command application, and randomize around that measured latency during training.

---

# Phase 16 — Calibrate the real camera

Measure camera intrinsics:

```text
fx, fy, cx, cy, distortion coefficients
```

Measure camera-to-robot extrinsics:

```text
camera frame -> robot base frame
```

Match the simulated camera as closely as practical in:

- Position and orientation
- Resolution
- Field of view
- Frame rate
- Exposure/lighting behavior
- Distortion or its preprocessing treatment

Keep all coordinate transforms explicit and test them with known points.

---

# Phase 17 — Build a safe real-robot inference loop

Conceptual loop:

```python
while robot_is_running:
    observation = get_observation()
    raw_action = policy(observation)
    safe_action = safety_filter(raw_action)
    robot.send_action(safe_action)
```

The safety filter must enforce:

- Joint position limits
- Joint velocity limits
- Per-step action limits
- Workspace limits
- Collision constraints where available
- Timeout behavior for missing observations
- A known safe/home behavior
- An easily reachable emergency stop

Never send unrestricted neural-network outputs directly to the physical robot.

Initial deployment should use reduced speed, small action bounds, an empty workspace, and a person ready to stop the arm.

---

# Phase 18 — Real-world test sequence

Run increasingly difficult tests:

1. Read joint states while motors remain safe.
2. Move to the home pose.
3. Command one small joint movement at a time.
4. Follow a slow known joint trajectory.
5. Reach one known Cartesian target.
6. Reach randomized safe targets.
7. Approach the cube without grasping.
8. Grasp and release without transport.
9. Lift a small distance.
10. Perform full pick-and-place.

Stop and diagnose at the first level that is not repeatable.

---

# Phase 19 — Compare simulation with reality

Maintain an evaluation table rather than relying on impressions:

| Environment | Episodes | Success rate | Main failures |
|---|---:|---:|---|
| Nominal simulation | | | |
| Randomized simulation | | | |
| Held-out randomization | | | |
| Real robot | | | |

Map failures to likely improvements:

| Failure source | Candidate response |
|---|---|
| Perception | Better camera calibration and visual randomization |
| Physics/contact | Measure mass/friction; revise physics ranges |
| Servo behavior | Improve actuator model and gain randomization |
| Latency | Measure and randomize control/sensor delay |
| Coordinate mismatch | Fix joint signs, offsets, units, or transforms |
| Unsafe/jittery action | Reduce action scale; add smoothing and limits |
| Reward exploit | Redesign reward and success conditions |

Use real-world failures to update the simulation distribution, retrain, and reevaluate. Do not tune only to one physical arrangement.

---

# Milestone checklist

## Infrastructure

- [x] Native Ubuntu 24.04
- [x] RTX 3080 detected on host
- [ ] Docker Engine installed and verified
- [ ] Docker usable without `sudo` if desired
- [ ] NVIDIA Container Toolkit installed
- [ ] RTX 3080 visible inside a CUDA container

## Isaac Sim and asset

- [ ] Compatible Isaac Sim image version pinned
- [ ] Isaac Sim starts with GPU acceleration
- [ ] Project folder mounts into the container
- [ ] SO-101 URDF and meshes stored locally
- [ ] SO-101 imported to USD
- [ ] Joint names/order/axes/signs/limits validated
- [ ] Gripper and collision geometry validated

## Isaac Lab task

- [ ] Minimal tabletop scene works
- [ ] Reset logic is reliable
- [ ] State observation vector documented
- [ ] Action convention documented and bounded
- [ ] Reaching policy works
- [ ] Grasp-and-lift policy works
- [ ] Pick-and-place policy works
- [ ] Nominal evaluation is repeatable
- [ ] Domain randomization added gradually
- [ ] Held-out randomized evaluation recorded

## Sim-to-real

- [ ] Real joint calibration completed
- [ ] Real motor dynamics measured
- [ ] Sensor/control latency measured
- [ ] Camera intrinsics and extrinsics calibrated
- [ ] Safety filter and emergency stop tested
- [ ] Small-motion hardware tests passed
- [ ] Reach tests passed
- [ ] Grasp tests passed
- [ ] Full pick-and-place evaluated
- [ ] Sim-versus-real gap documented and iterated

---

# Immediate next action

Continue only with Docker first:

```bash
docker --version
sudo systemctl status docker
sudo docker run hello-world
```

Once those pass, install NVIDIA Container Toolkit and run the containerized `nvidia-smi` test. Do not start the Isaac Sim or SO-101 import work until Docker can reliably see the RTX 3080.

Keep a short log after every milestone:

```text
date:
host driver version:
Docker version:
NVIDIA Container Toolkit version:
container image tag:
Isaac Sim version:
Isaac Lab version:
command run:
result:
error and fix:
```

That record will make the environment reproducible and will prevent version confusion later.
