"""Deterministic grasp-and-lift sequence for the SO-101 task."""

from dataclasses import dataclass

import numpy as np
from isaacsim.core.utils.types import ArticulationAction

from .kinematics import SO101PositionController
from .pick_place_task import SO101PickPlaceTask


@dataclass(frozen=True)
class GraspConfig:
    pre_grasp_clearance_m: float = 0.10
    grasp_height_offset_m: float = -0.012
    lift_clearance_m: float = 0.12
    gripper_open_rad: float = 0.9
    gripper_closed_rad: float = 0.0
    gripper_motion_steps: int = 150
    hold_steps: int = 120
    minimum_lift_m: float = 0.06
    maximum_grasp_distance_m: float = 0.06
    maximum_hold_drift_m: float = 0.015
    grasp_lateral_offset_m: float = -0.022
    descent_lateral_offset_m: float = -0.055


@dataclass(frozen=True)
class GraspResult:
    success: bool
    state_history: tuple[str, ...]
    cube_start_position: np.ndarray
    cube_lift_position: np.ndarray
    cube_after_close_position: np.ndarray
    grasp_end_effector_position: np.ndarray
    grasp_end_effector_rotation: np.ndarray
    grasp_joint_positions: np.ndarray
    cube_hold_position: np.ndarray
    end_effector_position: np.ndarray
    lift_height_m: float
    grasp_distance_m: float
    hold_drift_m: float
    gripper_position_rad: float


class SO101GraspController:
    """Execute RESET→APPROACH→DESCEND→ALIGN→CLOSE→LIFT→HOLD."""

    def __init__(
        self,
        task: SO101PickPlaceTask,
        position_controller: SO101PositionController,
        config: GraspConfig | None = None,
    ) -> None:
        self.task = task
        self.position_controller = position_controller
        self.config = config or GraspConfig()

    def set_gripper(self, target_rad: float) -> None:
        positions = self.task.robot.get_joint_positions().copy()
        start = float(positions[5])
        for step in range(1, self.config.gripper_motion_steps + 1):
            fraction = step / self.config.gripper_motion_steps
            positions[5] = start + fraction * (target_rad - start)
            self.task.robot.apply_action(
                ArticulationAction(joint_positions=positions.copy())
            )
            self.task.step(1)

    def execute(self) -> GraspResult:
        states = ["RESET"]
        self.task.reset(settle=True)
        self.set_gripper(self.config.gripper_open_rad)
        cube_start = self.task.get_state()["cube_position"]

        lateral = self.config.grasp_lateral_offset_m
        descent_lateral = self.config.descent_lateral_offset_m
        pre_grasp = cube_start + np.array(
            [0.0, descent_lateral, self.config.pre_grasp_clearance_m]
        )
        descent = cube_start + np.array(
            [0.0, descent_lateral, self.config.grasp_height_offset_m]
        )
        grasp = cube_start + np.array(
            [0.0, lateral, self.config.grasp_height_offset_m]
        )
        lift = cube_start + np.array(
            [0.0, lateral, self.config.lift_clearance_m]
        )

        states.append("APPROACH")
        self.position_controller.move_to("pre_grasp", pre_grasp)
        states.append("DESCEND")
        self.position_controller.move_to(
            "descent",
            descent,
            position_tolerance=self.config.maximum_grasp_distance_m,
        )
        states.append("ALIGN")
        self.position_controller.move_to(
            "grasp",
            grasp,
            position_tolerance=self.config.maximum_grasp_distance_m,
        )
        grasp_ee_position, grasp_ee_rotation = (
            self.position_controller.get_end_effector_pose()
        )
        grasp_joint_positions = self.task.robot.get_joint_positions().copy()
        states.append("CLOSE")
        self.set_gripper(self.config.gripper_closed_rad)
        cube_after_close = self.task.get_state()["cube_position"]
        states.append("VERIFY_GRASP")

        states.append("LIFT")
        self.position_controller.move_to("lift", lift)
        cube_lift = self.task.get_state()["cube_position"]
        ee_position = self.position_controller.get_end_effector_position()

        states.append("HOLD")
        self.task.step(self.config.hold_steps)
        hold_state = self.task.get_state()
        cube_hold = hold_state["cube_position"]

        lift_height = float(cube_lift[2] - cube_start[2])
        grasp_distance = float(np.linalg.norm(cube_hold - ee_position))
        hold_drift = float(np.linalg.norm(cube_hold - cube_lift))
        gripper_position = float(hold_state["joint_positions"][5])
        success = (
            lift_height >= self.config.minimum_lift_m
            and grasp_distance <= self.config.maximum_grasp_distance_m
            and hold_drift <= self.config.maximum_hold_drift_m
        )
        states.append("SUCCESS" if success else "FAILURE")
        return GraspResult(
            success=success,
            state_history=tuple(states),
            cube_start_position=cube_start.copy(),
            cube_lift_position=cube_lift.copy(),
            cube_after_close_position=cube_after_close.copy(),
            grasp_end_effector_position=grasp_ee_position.copy(),
            grasp_end_effector_rotation=grasp_ee_rotation.copy(),
            grasp_joint_positions=grasp_joint_positions.copy(),
            cube_hold_position=cube_hold.copy(),
            end_effector_position=ee_position.copy(),
            lift_height_m=lift_height,
            grasp_distance_m=grasp_distance,
            hold_drift_m=hold_drift,
            gripper_position_rad=gripper_position,
        )
