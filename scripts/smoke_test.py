"""Verify rendering, physics, and project writes; save a small local USD scene."""
from pathlib import Path
import json
from isaacsim import SimulationApp

app = SimulationApp({"headless": True, "width": 640, "height": 480})
try:
    import numpy as np
    import omni.usd
    from pxr import UsdGeom, UsdLux, Gf
    from isaacsim.core.api import World
    from isaacsim.core.api.objects import DynamicCuboid, FixedCuboid

    project = Path('/workspace/so101')
    world = World(stage_units_in_meters=1.0)
    # Local primitives avoid a dependency on downloading the default ground asset.
    world.scene.add(FixedCuboid(prim_path='/World/Ground', name='ground',
        position=np.array([0., 0., -0.05]), scale=np.array([4., 4., 0.1]),
        color=np.array([0.25, 0.25, 0.25])))
    cube = world.scene.add(DynamicCuboid(prim_path='/World/Cube', name='cube',
        position=np.array([0., 0., 0.5]), scale=np.array([0.1, 0.1, 0.1]),
        mass=0.1, color=np.array([0.15, 0.5, 0.9])))
    stage = omni.usd.get_context().get_stage()
    stage.SetDefaultPrim(stage.GetPrimAtPath('/World'))
    UsdLux.DistantLight.Define(stage, '/World/Light').CreateIntensityAttr(1500)
    world.reset()
    start, _ = cube.get_world_pose()
    for _ in range(120):
        world.step(render=True)
    end, _ = cube.get_world_pose()
    assert np.isfinite(end).all(), end
    assert 0.03 < float(end[2]) < 0.08, f'Cube did not settle on ground: {end}'
    assert float(start[2] - end[2]) > 0.3, 'Gravity did not move the cube'
    world.stop()
    cube.set_world_pose(position=np.array([0., 0., 0.5]))
    scene = project / 'scenes/environment_smoke_test.usd'
    assert stage.GetRootLayer().Export(str(scene)), 'USD export failed'
    result = {'result': 'PASS', 'physics_steps': 120,
              'start_position': start.tolist(), 'settled_position': end.tolist(),
              'scene': str(scene)}
    (project / 'logs/environment_smoke_test.json').write_text(json.dumps(result, indent=2) + '\n')
    print('SO101_SMOKE_TEST_PASS ' + json.dumps(result), flush=True)
finally:
    app.close()
