"""SO-101 articulation configuration for Isaac Lab 2.3.x."""

from isaaclab import sim as sim_utils
from isaaclab.actuators import ImplicitActuatorCfg
from isaaclab.assets import ArticulationCfg


SO101_JOINT_NAMES = (
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
)

SO101_CFG = ArticulationCfg(
    prim_path="{ENV_REGEX_NS}/Robot",
    spawn=sim_utils.UsdFileCfg(
        usd_path=(
            "/workspace/so101/assets/robots/so101/so101_new_calib/"
            "so101_new_calib.usd"
        ),
    ),
    init_state=ArticulationCfg.InitialStateCfg(
        joint_pos={".*": 0.0},
        joint_vel={".*": 0.0},
    ),
    actuators={
        "arm": ImplicitActuatorCfg(
            joint_names_expr=list(SO101_JOINT_NAMES[:5]),
            stiffness=None,
            damping=None,
        ),
        "gripper": ImplicitActuatorCfg(
            joint_names_expr=[SO101_JOINT_NAMES[5]],
            stiffness=None,
            damping=None,
        ),
    },
)
