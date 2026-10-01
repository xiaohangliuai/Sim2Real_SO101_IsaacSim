"""First SO-101 Isaac Lab task: reach a fixed end-effector target."""

from collections.abc import Sequence

import torch

from isaaclab.assets import Articulation, ArticulationCfg
from isaaclab.envs import DirectRLEnv, DirectRLEnvCfg
from isaaclab.scene import InteractiveSceneCfg
from isaaclab.sim import SimulationCfg
from isaaclab.utils import configclass

from .asset_cfg import SO101_CFG, SO101_JOINT_NAMES


@configclass
class SO101ReachEnvCfg(DirectRLEnvCfg):
    """A small state-only reaching task with bounded joint-position actions."""

    decimation = 2
    episode_length_s = 5.0
    action_space = 6
    observation_space = 24
    state_space = 0

    sim: SimulationCfg = SimulationCfg(dt=1.0 / 120.0, render_interval=decimation)
    scene: InteractiveSceneCfg = InteractiveSceneCfg(
        num_envs=8,
        env_spacing=2.0,
        replicate_physics=True,
        clone_in_fabric=False,
    )
    robot_cfg: ArticulationCfg = SO101_CFG.replace(
        prim_path="/World/envs/env_.*/Robot"
    )

    target_position = (0.300, 0.0, 0.100)
    arm_action_scale_rad = 0.02
    gripper_action_scale_rad = 0.04
    success_distance_m = 0.025


class SO101ReachEnv(DirectRLEnv):
    """Observe joint and tool state; command small joint-position increments."""

    cfg: SO101ReachEnvCfg

    def __init__(
        self,
        cfg: SO101ReachEnvCfg,
        render_mode: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(cfg, render_mode, **kwargs)
        if tuple(self.robot.joint_names) != SO101_JOINT_NAMES:
            raise RuntimeError(f"Unexpected SO-101 joints: {self.robot.joint_names}")
        self.ee_body_index = self.robot.body_names.index("gripper_frame_link")
        self.goal = torch.tensor(
            cfg.target_position,
            dtype=torch.float32,
            device=self.device,
        ).repeat(self.num_envs, 1)
        self.action_scale = torch.tensor(
            [cfg.arm_action_scale_rad] * 5 + [cfg.gripper_action_scale_rad],
            dtype=torch.float32,
            device=self.device,
        )
        self.actions = torch.zeros((self.num_envs, 6), device=self.device)
        self.joint_targets = self.robot.data.default_joint_pos.clone()

    def _setup_scene(self) -> None:
        self.robot = Articulation(self.cfg.robot_cfg)
        self.scene.clone_environments(copy_from_source=False)
        if self.device == "cpu":
            self.scene.filter_collisions(global_prim_paths=[])
        self.scene.articulations["robot"] = self.robot

    def _tool_position(self) -> torch.Tensor:
        return (
            self.robot.data.body_pos_w[:, self.ee_body_index, :]
            - self.scene.env_origins
        )

    def _pre_physics_step(self, actions: torch.Tensor) -> None:
        self.actions = torch.clamp(actions.clone(), -1.0, 1.0)
        requested = self.robot.data.joint_pos + self.actions * self.action_scale
        limits = self.robot.data.soft_joint_pos_limits
        self.joint_targets = torch.clamp(
            requested,
            min=limits[:, :, 0],
            max=limits[:, :, 1],
        )

    def _apply_action(self) -> None:
        self.robot.set_joint_position_target(self.joint_targets)

    def _get_observations(self) -> dict:
        policy = torch.cat(
            (
                self.robot.data.joint_pos,
                self.robot.data.joint_vel,
                self._tool_position(),
                self.goal,
                self.actions,
            ),
            dim=-1,
        )
        return {"policy": policy}

    def _get_rewards(self) -> torch.Tensor:
        distance = torch.linalg.vector_norm(
            self._tool_position() - self.goal,
            dim=1,
        )
        proximity = torch.exp(-4.0 * distance)
        action_penalty = 0.001 * torch.sum(self.actions.square(), dim=1)
        success_bonus = (distance < self.cfg.success_distance_m).float()
        return proximity - action_penalty + success_bonus

    def _get_dones(self) -> tuple[torch.Tensor, torch.Tensor]:
        distance = torch.linalg.vector_norm(
            self._tool_position() - self.goal,
            dim=1,
        )
        reached = distance < self.cfg.success_distance_m
        timeout = self.episode_length_buf >= self.max_episode_length - 1
        return reached, timeout

    def _reset_idx(self, env_ids: Sequence[int] | None) -> None:
        if env_ids is None:
            env_ids = self.robot._ALL_INDICES
        super()._reset_idx(env_ids)
        joint_pos = self.robot.data.default_joint_pos[env_ids].clone()
        joint_vel = self.robot.data.default_joint_vel[env_ids].clone()
        self.robot.write_joint_state_to_sim(
            joint_pos,
            joint_vel,
            env_ids=env_ids,
        )
        self.robot.set_joint_position_target(joint_pos, env_ids=env_ids)
        self.joint_targets[env_ids] = joint_pos
        self.actions[env_ids] = 0.0
