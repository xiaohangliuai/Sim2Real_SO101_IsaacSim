"""Position-priority Lula IK and smooth joint-space motion for SO-101."""

from dataclasses import dataclass

import numpy as np
from isaacsim.core.utils.types import ArticulationAction
from isaacsim.robot_motion.motion_generation import ArticulationKinematicsSolver
from isaacsim.robot_motion.motion_generation.lula.kinematics import LulaKinematicsSolver

from .pick_place_task import SO101PickPlaceTask


@dataclass(frozen=True)
class ReachResult:
    name: str
    target_position: np.ndarray
    achieved_position: np.ndarray
    position_error: float
    ik_success: bool
    joint_positions: np.ndarray


class SO101PositionController:
    """Solve position-only IK and apply interpolated joint position targets."""

    def __init__(
        self,
        task: SO101PickPlaceTask,
        robot_description_path: str,
        urdf_path: str,
        end_effector_frame: str = "gripper_frame_link",
    ) -> None:
        self.task = task
        self.robot = task.robot
        self.solver = LulaKinematicsSolver(robot_description_path, urdf_path)
        self.end_effector_frame = end_effector_frame
        if end_effector_frame not in self.solver.get_all_frame_names():
            raise RuntimeError(
                f"Unknown end-effector frame {end_effector_frame}; "
                f"available frames: {self.solver.get_all_frame_names()}"
            )
        lula_joint_names = self.solver.get_joint_names()
        expected_joint_names = task.expected_dof_names[: len(lula_joint_names)]
        if lula_joint_names != expected_joint_names:
            raise RuntimeError(
                f"Lula joint order {lula_joint_names} does not match "
                f"the articulation prefix {expected_joint_names}"
            )
        self._update_base_pose()
        self.articulation_solver = ArticulationKinematicsSolver(
            self.robot,
            self.solver,
            self.end_effector_frame,
        )

    def _update_base_pose(self) -> None:
        position, orientation = self.robot.get_world_pose()
        self.solver.set_robot_base_pose(position, orientation)

    def get_end_effector_pose(self) -> tuple[np.ndarray, np.ndarray]:
        self._update_base_pose()
        position, rotation = self.articulation_solver.compute_end_effector_pose()
        return (
            np.asarray(position, dtype=np.float64),
            np.asarray(rotation, dtype=np.float64),
        )

    def get_end_effector_position(self) -> np.ndarray:
        position, _ = self.get_end_effector_pose()
        return position

    def solve(self, target_position: np.ndarray, tolerance: float = 0.005):
        self._update_base_pose()
        return self.articulation_solver.compute_inverse_kinematics(
            target_position=np.asarray(target_position, dtype=np.float64),
            target_orientation=None,
            position_tolerance=tolerance,
        )

    def move_to(
        self,
        name: str,
        target_position: np.ndarray,
        interpolation_steps: int = 180,
        settle_steps: int = 90,
        position_tolerance: float = 0.02,
    ) -> ReachResult:
        target_position = np.asarray(target_position, dtype=np.float64)
        action, success = self.solve(target_position)
        if not success or action.joint_positions is None:
            raise RuntimeError(f"IK failed for {name} at {target_position.tolist()}")

        active_indices = np.asarray(action.joint_indices, dtype=np.int64)
        goal_active = np.asarray(action.joint_positions, dtype=np.float32)
        start = self.robot.get_joint_positions().copy()
        goal = start.copy()
        goal[active_indices] = goal_active

        limits = self.robot.dof_properties
        if np.any(goal < limits["lower"] - 1.0e-5) or np.any(
            goal > limits["upper"] + 1.0e-5
        ):
            raise RuntimeError(f"IK goal for {name} exceeds articulation limits: {goal}")

        for step in range(1, interpolation_steps + 1):
            fraction = step / interpolation_steps
            targets = start + fraction * (goal - start)
            self.robot.apply_action(ArticulationAction(joint_positions=targets))
            self.task.step(1)
        self.task.step(settle_steps)

        achieved = self.get_end_effector_position()
        error = float(np.linalg.norm(achieved - target_position))
        if error > position_tolerance:
            raise RuntimeError(
                f"{name} position error {error:.6f} m exceeds "
                f"{position_tolerance:.6f} m"
            )
        return ReachResult(
            name=name,
            target_position=target_position.copy(),
            achieved_position=achieved.copy(),
            position_error=error,
            ik_success=bool(success),
            joint_positions=self.robot.get_joint_positions().copy(),
        )
