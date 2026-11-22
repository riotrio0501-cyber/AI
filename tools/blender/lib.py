"""Blender用の共通部品：マテリアル、舞台（雪原・空・照明）、カメラ、レンダー設定。

bpy（Blenderのpython版）で動く。python3 から import bpy して使う。
"""
from __future__ import annotations

import math

import bpy
from mathutils import Vector

W, H, FPS = 1080, 1920, 30


# ---------- 基本 ----------
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.fps = FPS
    return sc


def link(obj, parent=None):
    bpy.context.scene.collection.objects.link(obj)
    if parent is not None:
        obj.parent = parent
    return obj


def empty(name, loc=(0, 0, 0), parent=None):
    e = bpy.data.objects.new(name, None)
    e.location = loc
    e.empty_display_size = 0.2
    return link(e, parent)


def smooth(obj, subdiv=2):
    for p in obj.data.polygons:
        p.use_smooth = True
    if subdiv:
        m = obj.modifiers.new("subd", "SUBSURF")
        m.levels = m.render_levels = subdiv
    return obj


def sphere(name, r=1.0, loc=(0, 0, 0), scale=(1, 1, 1), mat=None, parent=None, seg=32, subdiv=1):
    import bmesh
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=r)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.location, ob.scale = loc, scale
    link(ob, parent)
    if mat:
        ob.data.materials.append(mat)
    return smooth(ob, subdiv)


def capsule(name, r, length, loc, rot=(0, 0, 0), mat=None, parent=None):
    """丸い棒（足・しっぽ用）。"""
    ob = sphere(name, r, loc, (1, 1, length / (2 * r)), mat, parent, seg=24)
    ob.rotation_euler = rot
    return ob


# ---------- マテリアル ----------
def _nodes(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    return m, nt, bsdf


def mat_soft(name, color, rough=0.55, sss=0.25, sheen=0.6, sss_radius=(0.4, 0.2, 0.1)):
    """やわらかい毛・肌っぽい質感（表面のうぶ毛のようなツヤ＋光の透け）。"""
    m, nt, b = _nodes(name)
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Subsurface Weight"].default_value = sss
    b.inputs["Subsurface Radius"].default_value = sss_radius
    b.inputs["Subsurface Scale"].default_value = 0.05
    b.inputs["Sheen Weight"].default_value = sheen
    b.inputs["Sheen Tint"].default_value = (1, 1, 1, 1)
    # ふわっとした細かい凹凸
    tex = nt.nodes.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = 180
    tex.inputs["Detail"].default_value = 6
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.12
    bump.inputs["Distance"].default_value = 0.002
    nt.links.new(tex.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def mat_gloss(name, color, rough=0.15):
    m, nt, b = _nodes(name)
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Coat Weight"].default_value = 0.5
    return m


def mat_shell(name, base, line, scale=7.0, width=0.05):
    """六角っぽい甲羅もよう（ボロノイの境目を濃い色の線にする）。"""
    m, nt, b = _nodes(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.feature = "DISTANCE_TO_EDGE"
    vor.inputs["Scale"].default_value = scale
    vor.inputs["Randomness"].default_value = 0.35
    nt.links.new(tc.outputs["Object"], vor.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = width * 0.6
    ramp.color_ramp.elements[0].color = (*line, 1)
    ramp.color_ramp.elements[1].position = width
    ramp.color_ramp.elements[1].color = (*base, 1)
    nt.links.new(vor.outputs["Distance"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.35
    b.inputs["Coat Weight"].default_value = 0.3
    b.inputs["Subsurface Weight"].default_value = 0.1
    b.inputs["Subsurface Radius"].default_value = (0.6, 0.3, 0.1)
    b.inputs["Subsurface Scale"].default_value = 0.03
    # 板ごとのふくらみ（境目をへこませる）
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.6
    bump.inputs["Distance"].default_value = 0.02
    nt.links.new(vor.outputs["Distance"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def mat_eye(name, iris, iris_r=0.62, pupil_r=0.33):
    """目玉：物体の -Y 方向が正面。中心からの距離で 黒目・虹彩・白目 を塗り分ける。"""
    m, nt, b = _nodes(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
    # r = sqrt(x^2 + z^2)（オブジェクト座標は半径1基準）
    mx = nt.nodes.new("ShaderNodeMath"); mx.operation = "MULTIPLY"
    mz = nt.nodes.new("ShaderNodeMath"); mz.operation = "MULTIPLY"
    add = nt.nodes.new("ShaderNodeMath"); add.operation = "ADD"
    sq = nt.nodes.new("ShaderNodeMath"); sq.operation = "SQRT"
    nt.links.new(sep.outputs["X"], mx.inputs[0]); nt.links.new(sep.outputs["X"], mx.inputs[1])
    nt.links.new(sep.outputs["Z"], mz.inputs[0]); nt.links.new(sep.outputs["Z"], mz.inputs[1])
    nt.links.new(mx.outputs[0], add.inputs[0]); nt.links.new(mz.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], sq.inputs[0])
    # 後ろ側（y>0）は白目にするため r を大きく
    gt = nt.nodes.new("ShaderNodeMath"); gt.operation = "GREATER_THAN"; gt.inputs[1].default_value = 0.0
    nt.links.new(sep.outputs["Y"], gt.inputs[0])
    big = nt.nodes.new("ShaderNodeMath"); big.operation = "MULTIPLY_ADD"
    big.inputs[1].default_value = 5.0
    nt.links.new(gt.outputs[0], big.inputs[0]); nt.links.new(sq.outputs[0], big.inputs[2])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.interpolation = "EASE"
    cr.elements[0].position, cr.elements[0].color = pupil_r - 0.02, (0.01, 0.01, 0.01, 1)
    cr.elements[1].position, cr.elements[1].color = iris_r + 0.02, (0.95, 0.95, 0.93, 1)
    e = cr.elements.new(pupil_r + 0.03); e.color = (*[c * 0.55 for c in iris], 1)
    e = cr.elements.new(iris_r - 0.06); e.color = (*iris, 1)
    e = cr.elements.new(iris_r - 0.005); e.color = (*[c * 0.35 for c in iris], 1)
    nt.links.new(big.outputs[0], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.03
    b.inputs["Coat Weight"].default_value = 1.0
    b.inputs["Subsurface Weight"].default_value = 0.1
    return m


def mat_snow(name="snow"):
    m, nt, b = _nodes(name)
    b.inputs["Base Color"].default_value = (0.86, 0.91, 0.98, 1)
    b.inputs["Roughness"].default_value = 0.7
    b.inputs["Subsurface Weight"].default_value = 0.6
    b.inputs["Subsurface Radius"].default_value = (0.5, 0.7, 1.0)
    b.inputs["Subsurface Scale"].default_value = 0.1
    b.inputs["Sheen Weight"].default_value = 0.4
    tex = nt.nodes.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = 40
    tex.inputs["Detail"].default_value = 8
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.25
    nt.links.new(tex.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


# ---------- 舞台 ----------
def world_sky(top=(0.35, 0.55, 0.85), bottom=(0.85, 0.92, 1.0), strength=1.0):
    w = bpy.data.worlds.new("sky")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes["Background"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*bottom, 1)
    ramp.color_ramp.elements[1].position = 0.5
    ramp.color_ramp.elements[1].color = (*top, 1)
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = strength


def snow_ground(size=40):
    bpy.ops.mesh.primitive_plane_add(size=size)
    g = bpy.context.active_object
    g.name = "ground"
    bpy.ops.object.mode_set(mode="OBJECT")
    m = g.modifiers.new("subd", "SUBSURF"); m.subdivision_type = "SIMPLE"; m.levels = m.render_levels = 6
    tex = bpy.data.textures.new("drift", "CLOUDS"); tex.noise_scale = 3.0
    d = g.modifiers.new("disp", "DISPLACE"); d.texture = tex; d.strength = 0.25; d.mid_level = 0.5
    for p in g.data.polygons:
        p.use_smooth = True
    g.data.materials.append(mat_snow())
    return g


def lights(key_energy=4.0, key_color=(1.0, 0.88, 0.7)):
    sun = bpy.data.lights.new("key", "SUN")
    sun.energy = key_energy
    sun.color = key_color
    sun.angle = math.radians(8)
    ob = link(bpy.data.objects.new("key", sun))
    ob.rotation_euler = (math.radians(50), 0, math.radians(-35))
    rim = bpy.data.lights.new("rim", "AREA")
    rim.energy = 400
    rim.color = (0.6, 0.8, 1.0)
    rim.size = 4
    ob2 = link(bpy.data.objects.new("rim", rim))
    ob2.location = (2.5, 3.5, 3)
    look_at(ob2, (0, 0, 0.5))


def look_at(obj, target):
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def camera(loc=(0, -4, 0.8), target=(0, 0, 0.5), lens=50, dof_dist=None, fstop=2.8):
    cam = bpy.data.cameras.new("cam")
    cam.lens = lens
    cam.sensor_fit = "VERTICAL"
    ob = link(bpy.data.objects.new("cam", cam))
    ob.location = loc
    look_at(ob, target)
    bpy.context.scene.camera = ob
    if dof_dist:
        cam.dof.use_dof = True
        cam.dof.focus_distance = dof_dist
        cam.dof.aperture_fstop = fstop
    return ob


def render_settings(samples=48, engine="CYCLES", preview=False):
    sc = bpy.context.scene
    sc.render.engine = engine
    if engine == "CYCLES":
        sc.cycles.device = "CPU"
        sc.cycles.samples = samples
        sc.cycles.use_denoising = True
        sc.cycles.max_bounces = 6
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    if preview:
        sc.render.resolution_percentage = 50
    return sc


def render_still(path):
    sc = bpy.context.scene
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
