"""Complete deterministic SO-101 pick-and-place sequence."""

from dataclasses import dataclass

import numpy as np
from isaacsim.core.utils.types import ArticulationAction

from .grasp import GraspResult, SO101GraspController
from .kinematics import SO101PositionController
from .pick_place_task import SO101PickPlaceTask


@dataclass(frozen=True)
class PickPlaceConfig:
    target_cube_height_offset_m: float = 0.019
    release_compensation_x_m: float = 0.014
    release_compensation_y_m: float = -0.012
    pre_place_clearance_m: float = 0.12
    place_approach_clearance_m: float = 0.04
    correction_iterations: int = 3
    exit_distance_m: float = 0.045
    retreat_clearance_m: float = 0.12
    release_settle_steps: int = 120
    final_settle_steps: int = 240
    home_motion_steps: int = 300
    maximum_target_xy_error_m: float = 0.025
    maximum_height_error_m: float = 0.008
    maximum_final_speed_m_s: float = 0.01
    maximum_home_error_rad: float = 0.03


@dataclass(frozen=True)
class PickPlaceResult:
    success: bool
    state_history: tuple[str, ...]
    grasp: GraspResult
    desired_cube_position: np.ndarray
    placed_cube_position: np.ndarray
    released_cube_position: np.ndarray
    final_cube_position: np.ndarray
    final_cube_velocity: np.ndarray
    final_joint_positions: np.ndarray
    target_xy_error_m: float
    height_error_m: float
    final_speed_m_s: float
    home_error_rad: float


class SO101PickPlaceController:
    """Grasp, transfer, place, release, retreat, and return home."""

    def __init__(
        self,
        task: SO101PickPlaceTask,
        position_controller: SO101PositionController,
        grasp_controller: SO101GraspController,
        config: PickPlaceConfig | None = None,
    ) -> None:
        self.task = task
        self.position_controller = position_controller
        self.grasp_controller = grasp_controller
        self.config = config or PickPlaceConfig()

    def _move_cube_to(self, name: str, desired_cube_position: np.ndarray) -> None:
        for correction in range(self.config.correction_iterations):
            state = self.task.get_state()
            end_effector = self.position_controller.get_end_effector_position()
            target_end_effector = end_effector + (
                desired_cube_position - state["cube_position"]
            )
            self.position_controller.move_to(
                f"{name}_{correction + 1}",
                target_end_effector,
                position_tolerance=0.04,
                joint_position_overrides={
                    5: self.grasp_controller.config.gripper_closed_rad
                },
            )

    def _return_home(self) -> None:
        start = self.task.robot.get_joint_positions().copy()
        goal = self.task.config.home_joint_positions.copy()
        goal[5] = self.grasp_controller.config.gripper_open_rad
        for step in range(1, self.config.home_motion_steps + 1):
            fraction = step / self.config.home_motion_steps
            targets = start + fraction * (goal - start)
            self.task.robot.apply_action(ArticulationAction(joint_positions=targets))
            self.task.step(1)
        self.grasp_controller.set_gripper(
            self.grasp_controller.config.gripper_closed_rad
        )

    def execute(self) -> PickPlaceResult:
        grasp = self.grasp_controller.execute()
        if not grasp.success:
            raise RuntimeError("Cannot place because the grasp-and-lift stage failed")

        states = list(grasp.state_history[:-1])
        target = self.task.get_state()["target_position"]
        desired_cube = target + np.array(
            [0.0, 0.0, self.config.target_cube_height_offset_m]
        )
        placement_cube = desired_cube + np.array(
            [
                self.config.release_compensation_x_m,
                self.config.release_compensation_y_m,
                0.0,
            ]
        )

        states.append("TRANSIT")
        self._move_cube_to(
            "pre_place",
            placement_cube
            + np.array([0.0, 0.0, self.config.pre_place_clearance_m]),
        )

        states.append("PLACE_APPROACH")
        self._move_cube_to(
            "place_approach",
            placement_cube
            + np.array([0.0, 0.0, self.config.place_approach_clearance_m]),
        )

        states.append("PLACE")
        place_state = self.task.get_state()
        end_effector = self.position_controller.get_end_effector_position()
        place_target = end_effector.copy()
        place_target[2] += placement_cube[2] - place_state["cube_position"][2]
        self.position_controller.move_to(
            "place",
            place_target,
            position_tolerance=0.04,
            joint_position_overrides={
                5: self.grasp_controller.config.gripper_closed_rad
            },
        )
        placed_cube = self.task.get_state()["cube_position"]

        states.append("OPEN")
        self.grasp_controller.set_gripper(
            self.grasp_controller.config.gripper_open_rad
        )
        self.task.step(self.config.release_settle_steps)
        released_cube = self.task.get_state()["cube_position"]

        states.append("EXIT")
        end_effector = self.position_controller.get_end_effector_position()
        horizontal_away = end_effector[:2] - released_cube[:2]
        norm = float(np.linalg.norm(horizontal_away))
        if norm < 1.0e-6:
            horizontal_away = np.array([0.0, -1.0])
        else:
            horizontal_away /= norm
        exit_position = end_effector.copy()
        exit_position[:2] += horizontal_away * self.config.exit_distance_m
        self.position_controller.move_to(
            "exit",
            exit_position,
            position_tolerance=0.04,
            joint_position_overrides={
                5: self.grasp_controller.config.gripper_open_rad
            },
        )

        states.append("RETREAT")
        retreat = self.position_controller.get_end_effector_position()
        retreat[2] += self.config.retreat_clearance_m
        self.position_controller.move_to(
            "retreat",
            retreat,
            joint_position_overrides={
                5: self.grasp_controller.config.gripper_open_rad
            },
        )

        states.append("HOME")
        self._return_home()
        self.task.step(self.config.final_settle_steps)
        final_state = self.task.get_state()

        final_cube = final_state["cube_position"]
        final_velocity = final_state["cube_linear_velocity"]
        final_joints = final_state["joint_positions"]
        target_xy_error = float(np.linalg.norm(final_cube[:2] - target[:2]))
        height_error = float(abs(final_cube[2] - desired_cube[2]))
        final_speed = float(np.linalg.norm(final_velocity))
        home_error = float(
            np.max(np.abs(final_joints - self.task.config.home_joint_positions))
        )
        success = (
            target_xy_error <= self.config.maximum_target_xy_error_m
            and height_error <= self.config.maximum_height_error_m
            and final_speed <= self.config.maximum_final_speed_m_s
            and home_error <= self.config.maximum_home_error_rad
        )
        states.append("SUCCESS" if success else "FAILURE")
        return PickPlaceResult(
            success=success,
            state_history=tuple(states),
            grasp=grasp,
            desired_cube_position=desired_cube.copy(),
            placed_cube_position=placed_cube.copy(),
            released_cube_position=released_cube.copy(),
            final_cube_position=final_cube.copy(),
            final_cube_velocity=final_velocity.copy(),
            final_joint_positions=final_joints.copy(),
            target_xy_error_m=target_xy_error,
            height_error_m=height_error,
            final_speed_m_s=final_speed,
            home_error_rad=home_error,
        )
