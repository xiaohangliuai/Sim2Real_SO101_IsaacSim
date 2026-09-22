"""Reusable state and deterministic reset logic for the SO-101 task."""

from dataclasses import dataclass, field

import numpy as np
from isaacsim.core.api import World
from isaacsim.core.prims import RigidPrim, SingleArticulation, XFormPrim
from isaacsim.core.utils.types import ArticulationAction


@dataclass(frozen=True)
class PickPlaceResetConfig:
    """Canonical task paths and reset state in SI units."""

    robot_prim_path: str = "/World/so101_new_calib"
    cube_prim_path: str = "/World/TaskObjects/PickCube"
    target_prim_path: str = "/World/TaskObjects/PlaceTarget"
    home_joint_positions: np.ndarray = field(
        default_factory=lambda: np.zeros(6, dtype=np.float32)
    )
    cube_position: np.ndarray = field(
        default_factory=lambda: np.array([0.2, 0.05, 0.8], dtype=np.float32)
    )
    cube_orientation: np.ndarray = field(
        default_factory=lambda: np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
    )
    target_position: np.ndarray = field(
        default_factory=lambda: np.array([-0.1, 0.05, 0.751], dtype=np.float32)
    )
    target_orientation: np.ndarray = field(
        default_factory=lambda: np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
    )
    settle_steps: int = 120


class SO101PickPlaceTask:
    """Own the scene views needed by scripted control and repeatable resets."""

    expected_dof_names = [
        "shoulder_pan",
        "shoulder_lift",
        "elbow_flex",
        "wrist_flex",
        "wrist_roll",
        "gripper",
    ]

    def __init__(self, world: World, config: PickPlaceResetConfig | None = None) -> None:
        self.world = world
        self.config = config or PickPlaceResetConfig()
        self.robot = world.scene.add(
            SingleArticulation(
                prim_path=self.config.robot_prim_path,
                name="so101",
                reset_xform_properties=False,
            )
        )
        self.cube = world.scene.add(
            RigidPrim(
                prim_paths_expr=self.config.cube_prim_path,
                name="pick_cube",
                reset_xform_properties=False,
            )
        )
        self.target = world.scene.add(
            XFormPrim(
                prim_paths_expr=self.config.target_prim_path,
                name="place_target",
                reset_xform_properties=False,
            )
        )

    def initialize(self) -> None:
        """Initialize physics handles and validate the controller contract."""

        self.world.reset()
        if self.robot.dof_names != self.expected_dof_names:
            raise RuntimeError(
                f"Unexpected DOF order: {self.robot.dof_names}; "
                f"expected {self.expected_dof_names}"
            )
        if self.robot.num_dof != len(self.config.home_joint_positions):
            raise RuntimeError(
                f"Home pose has {len(self.config.home_joint_positions)} values for "
                f"{self.robot.num_dof} DOFs"
            )

    def step(self, count: int, render: bool = False) -> None:
        for _ in range(count):
            self.world.step(render=render)

    def reset(self, settle: bool = True) -> dict:
        """Restore all task state, clear velocities, and optionally settle physics."""

        home = self.config.home_joint_positions.copy()
        zeros = np.zeros(self.robot.num_dof, dtype=np.float32)

        self.robot.set_joint_positions(home)
        self.robot.set_joint_velocities(zeros)
        self.robot.apply_action(ArticulationAction(joint_positions=home.copy()))

        self.cube.set_world_poses(
            positions=self.config.cube_position[None, :].copy(),
            orientations=self.config.cube_orientation[None, :].copy(),
        )
        self.cube.set_linear_velocities(np.zeros((1, 3), dtype=np.float32))
        self.cube.set_angular_velocities(np.zeros((1, 3), dtype=np.float32))

        self.target.set_world_poses(
            positions=self.config.target_position[None, :].copy(),
            orientations=self.config.target_orientation[None, :].copy(),
        )

        if settle:
            self.step(self.config.settle_steps)
        return self.get_state()

    def get_state(self) -> dict:
        cube_positions, cube_orientations = self.cube.get_world_poses()
        target_positions, target_orientations = self.target.get_world_poses()
        return {
            "joint_positions": self.robot.get_joint_positions().copy(),
            "joint_velocities": self.robot.get_joint_velocities().copy(),
            "cube_position": cube_positions[0].copy(),
            "cube_orientation": cube_orientations[0].copy(),
            "cube_linear_velocity": self.cube.get_linear_velocities()[0].copy(),
            "cube_angular_velocity": self.cube.get_angular_velocities()[0].copy(),
            "target_position": target_positions[0].copy(),
            "target_orientation": target_orientations[0].copy(),
        }
