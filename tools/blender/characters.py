"""キャラの3Dモデルを組み立てる（characters.md の設定どおり）。

各関数は「親」の空オブジェクトを返す。動かすときは親や名前付きのパーツ
（例: goro.eye_L, goro.lid_L, goro.mouth）を動かす。正面は -Y 方向。
"""
from __future__ import annotations

import math

import bmesh
import bpy

from lib import capsule, empty, link, mat_eye, mat_gloss, mat_shell, mat_soft, smooth, sphere

# 色（リニア値）。characters.md の文章に合わせる
CARAMEL = (0.55, 0.16, 0.025)
CHOCO_LINE = (0.07, 0.025, 0.01)
CREAM = (0.74, 0.5, 0.27)
EMERALD = (0.03, 0.5, 0.14)
PINK = (0.85, 0.32, 0.38)


def _shell_mesh(name, r, mat, parent, loc):
    """前と下が開いた、ドーム状の甲羅。"""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=r)
    kill = []
    for v in bm.verts:
        d = v.co.normalized()
        # 顔の開口部（前方の楕円）と、お腹側（下）を抜く
        face_open = (d.y < -0.25) and (d.x * d.x * 1.15 + d.z ** 2 * 1.8 < 0.55)
        if face_open or d.z < -0.55 or (d.y < 0.1 and d.z < -0.2):
            kill.append(v)
    bmesh.ops.delete(bm, geom=kill, context="VERTS")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    link(ob, parent)
    ob.data.materials.append(mat)
    sol = ob.modifiers.new("thick", "SOLIDIFY")
    sol.thickness = 0.07
    sol.offset = 1
    sol.use_rim = True
    sol.material_offset_rim = 1  # ふちは濃い茶色（固い甲羅に見せる）
    ob.data.materials.append(mat_gloss(name + "_rim", (0.12, 0.04, 0.01), 0.3))
    smooth(ob, 2)
    return ob


def _chip(target, loc, r):
    """甲羅の欠け（目じるし）：小さい球で削る。"""
    cutter = sphere(target.name + "_chipcutter", r, loc, parent=target.parent, subdiv=0)
    cutter.hide_render = True
    cutter.display_type = "WIRE"
    mod = target.modifiers.new("chip", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    # 欠けはサブディビジョンの後に入れる（角が立ってそれっぽい）
    return cutter


def _eye(prefix, side, loc, r, iris, skin, parent):
    """目玉＋まぶた（上下）。まぶたは回転させて開け閉めする。"""
    pivot = empty(f"{prefix}.eye_{side}", loc, parent)
    eye = sphere(f"{prefix}.eyeball_{side}", 1.0, (0, 0, 0), (r, r, r), mat=mat_eye(f"{prefix}_eye", iris), parent=pivot)
    lid_mat = skin
    lids = []
    for which, rot in (("up", -62), ("low", 62)):
        lid = _half_sphere(f"{prefix}.lid{which}_{side}", r * 1.06, lid_mat, pivot)
        lid.rotation_euler = (math.radians(rot + (0 if which == "up" else 180)), 0, 0)
        lids.append(lid)
    return pivot, eye, lids


def _half_sphere(name, r, mat, parent):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=r)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -1e-4], context="VERTS")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    link(ob, parent)
    ob.data.materials.append(mat)
    sol = ob.modifiers.new("thick", "SOLIDIFY"); sol.thickness = 0.01
    return smooth(ob, 1)


def _smile(name, mat, parent, loc, width=0.09, thick=0.014):
    """にっこり口（ドーナツの下半分）。scale z をマイナスにすると への字口になる。"""
    bpy.ops.mesh.primitive_torus_add(major_radius=width, minor_radius=thick, major_segments=40, minor_segments=10)
    ob = bpy.context.active_object
    ob.name = name
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y > -width * 0.35], context="VERTS")
    bm.to_mesh(ob.data)
    bm.free()
    ob.rotation_euler = (math.radians(90), 0, 0)
    ob.location = loc
    ob.parent = parent
    ob.data.materials.append(mat)
    return smooth(ob, 1)


def build_goro(loc=(0, 0, 0), name="goro"):
    root = empty(name, loc)
    body = empty(f"{name}.body", (0, 0, 0.5), root)  # 体の中心（転がるときはここを回す）

    m_shell = mat_shell("goro_shell", CARAMEL, CHOCO_LINE, scale=4.2, width=0.035)
    m_cream = mat_soft("goro_cream", CREAM, sss=0.3)
    m_feet = mat_soft("goro_feet", (0.45, 0.28, 0.16), sss=0.2)
    m_nose = mat_gloss("goro_nose", PINK, 0.3)
    m_mouth = mat_soft("goro_mouth", (0.18, 0.02, 0.03), sheen=0)

    # 中身（クリーム色の体）
    sphere(f"{name}.belly", 0.47, (0, -0.02, -0.02), (1, 0.98, 0.95), m_cream, body)
    # 甲羅
    shell = _shell_mesh(f"{name}.shell", 0.5, m_shell, body, (0, 0.02, 0.0))
    _chip(shell, (-0.2, -0.4, 0.3), 0.1)  # 見る人から見て左上

    # 目（大きい・エメラルドグリーン）
    eyes = {}
    for side, x in (("L", 0.15), ("R", -0.15)):
        pivot, eye, lids = _eye(name, side, (x, -0.38, 0.12), 0.13, EMERALD, m_cream, body)
        pivot.rotation_euler = (0, 0, math.radians(-14 if x > 0 else 14))
        eyes[side] = pivot
    # 鼻・口・ほっぺ
    sphere(f"{name}.nose", 0.04, (0, -0.5, -0.02), (1.3, 0.9, 0.8), m_nose, body)
    mouth = _smile(f"{name}.mouth", m_mouth, body, (0, -0.455, -0.1))
    mouth_open = sphere(f"{name}.mouth_open", 0.07, (0, -0.45, -0.14), (1.1, 0.5, 0.9), m_mouth, body)
    mouth_open.scale = (0.001, 0.001, 0.001)  # ふだんは隠す（びっくり顔で大きくする）
    for x in (0.27, -0.27):
        sphere(f"{name}.cheek", 0.1, (x, -0.34, -0.06), (1, 0.7, 0.8), mat_soft("goro_cheek", (0.95, 0.6, 0.5), sss=0.3), body)
    # 耳（小さく丸い）
    for x in (0.24, -0.24):
        sphere(f"{name}.ear", 0.07, (x * 1.35, -0.3, 0.17), (1, 0.45, 1), m_cream, body)
    # 足（短く太い）
    for x, y in ((0.2, -0.18), (-0.2, -0.18), (0.2, 0.2), (-0.2, 0.2)):
        capsule(f"{name}.leg", 0.085, 0.2, (x, y, -0.42), mat=m_feet, parent=body)
    # しっぽ（先が丸いこぶ）
    tail = empty(f"{name}.tail", (0, 0.47, -0.3), body)
    capsule(f"{name}.tail_stem", 0.05, 0.2, (0, 0.08, -0.02), (math.radians(-70), 0, 0), m_shell, tail)
    sphere(f"{name}.tail_knob", 0.08, (0, 0.18, -0.06), mat=m_shell, parent=tail)

    root["parts"] = {"body": body.name, "mouth": mouth.name, "tail": tail.name}
    return root


# ---------------- ピピ ----------------
SLATE = (0.035, 0.07, 0.15)
WHITE = (0.85, 0.87, 0.9)
ORANGE = (0.9, 0.3, 0.02)
YELLOW_CHEEK = (0.95, 0.55, 0.05)
AMBER = (0.75, 0.38, 0.03)


def _tuft(name, mat, parent, loc, r=0.05):
    """頭のてっぺんの、くるんと巻いた羽1本（らせんのカーブ）。"""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.018
    cu.bevel_resolution = 4
    sp = cu.splines.new("POLY")
    pts = []
    n = 30
    for i in range(n):
        k = i / (n - 1)
        if k < 0.45:  # まっすぐ上へ
            pts.append((0, -0.02 * k, k / 0.45 * 0.12))
        else:  # 前にくるんと巻く
            a = (k - 0.45) / 0.55 * math.radians(300)
            rr = r * (1 - 0.45 * (k - 0.45) / 0.55)
            pts.append((0, -0.009 - (rr - rr * math.cos(a)), 0.12 + rr * math.sin(a)))
    sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts):
        p.co = (*c, 1)
    # 先に行くほど細く
    for i, p in enumerate(sp.points):
        p.radius = 1.2 - 0.8 * i / (len(pts) - 1)
    ob = bpy.data.objects.new(name, cu)
    ob.location = loc
    link(ob, parent)
    ob.data.materials.append(mat)
    return ob


def build_pipi(loc=(0, 0, 0), name="pipi"):
    root = empty(name, loc)
    body = empty(f"{name}.body", (0, 0, 0.42), root)
    m_back = mat_soft("pipi_back", SLATE, rough=0.35, sss=0.1, sheen=0.3)
    m_belly = mat_soft("pipi_belly", WHITE, sss=0.35)
    m_orange = mat_gloss("pipi_orange", ORANGE, 0.35)
    m_cheek = mat_soft("pipi_cheek", YELLOW_CHEEK, sss=0.3, sheen=0.3)
    m_mouth = mat_soft("pipi_mouth", (0.12, 0.02, 0.02), sheen=0)

    sphere(f"{name}.torso", 0.36, (0, 0, 0), (1, 0.95, 1.18), m_back, body)       # たまご型
    sphere(f"{name}.belly", 0.33, (0, -0.06, -0.04), (0.92, 0.9, 1.08), m_belly, body)
    for side, x in (("L", 0.13), ("R", -0.13)):
        pivot, _, _ = _eye(name, side, (x, -0.27, 0.16), 0.1, AMBER, m_back, body)
        pivot.rotation_euler = (0, 0, math.radians(-16 if x > 0 else 16))
        sphere(f"{name}.cheek_{side}", 0.075, (x * 1.7, -0.25, 0.04), (1, 0.6, 0.8), m_cheek, body)
    # くちばし（短い）
    beak = sphere(f"{name}.beak", 0.07, (0, -0.37, 0.06), (1.1, 1.3, 0.6), m_orange, body)
    _smile(f"{name}.mouth", m_mouth, body, (0, -0.35, -0.02), width=0.05, thick=0.01)
    # つばさ
    for side, x in (("L", 1), ("R", -1)):
        w = empty(f"{name}.wing_{side}", (x * 0.33, 0.02, 0.05), body)
        sphere(f"{name}.wingmesh_{side}", 0.2, (x * 0.03, 0, -0.12), (0.25, 0.6, 1.0), m_back, w)
        w.rotation_euler = (0, math.radians(x * 12), 0)
    # 足
    for x in (0.12, -0.12):
        sphere(f"{name}.foot", 0.09, (x, -0.12, -0.42), (0.9, 1.4, 0.35), m_orange, body)
    _tuft(f"{name}.tuft", m_back, body, (0, -0.06, 0.38), r=0.075)
    root["parts"] = {"body": body.name, "beak": beak.name}
    return root


# ---------------- ドンさん ----------------
DARK_CHOCO = (0.035, 0.014, 0.006)
TAN = (0.42, 0.25, 0.1)
GRAY_BROW = (0.16, 0.16, 0.17)
TEETH = (0.85, 0.36, 0.05)
DARK_EYE = (0.12, 0.05, 0.02)


def mat_tail(name):
    """しっぽ：こうし模様（ななめの格子）。"""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Rotation"].default_value = (0, 0, math.radians(45))
    mp.inputs["Scale"].default_value = (9, 9, 9)
    ch = nt.nodes.new("ShaderNodeTexBrick")
    ch.inputs["Mortar Size"].default_value = 0.06
    ch.inputs["Color1"].default_value = (0.09, 0.07, 0.06, 1)
    ch.inputs["Color2"].default_value = (0.11, 0.08, 0.07, 1)
    ch.inputs["Mortar"].default_value = (0.03, 0.02, 0.02, 1)
    ch.offset = 0
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], ch.inputs["Vector"])
    nt.links.new(ch.outputs["Color"], b.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.5
    nt.links.new(ch.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.5
    return m


def build_don(loc=(0, 0, 0), name="don"):
    root = empty(name, loc)
    body = empty(f"{name}.body", (0, 0, 0), root)
    m_fur = mat_soft("don_fur", DARK_CHOCO, rough=0.7, sss=0.15, sheen=0.35)
    m_tan = mat_soft("don_tan", TAN, sss=0.2, sheen=0.7)
    m_brow = mat_soft("don_brow", GRAY_BROW, rough=0.9, sheen=0.5)
    m_teeth = mat_gloss("don_teeth", TEETH, 0.3)
    m_nose = mat_gloss("don_nose", (0.02, 0.015, 0.015), 0.25)
    m_twig = mat_soft("don_twig", (0.25, 0.13, 0.05), rough=0.8, sheen=0)
    m_mouth = mat_soft("don_mouth", (0.08, 0.01, 0.01), sheen=0)

    # 洋なし型の体（下が太い）
    torso = sphere(f"{name}.torso", 1.0, (0, 0, 1.15), (1.05, 0.92, 1.2), m_fur, body)
    tp = torso.modifiers.new("pear", "SIMPLE_DEFORM")
    tp.deform_method = "TAPER"
    tp.factor = -0.35
    tp.deform_axis = "Z"
    sphere(f"{name}.belly", 0.75, (0, -0.48, 0.95), (1, 0.7, 1.1), m_tan, body)
    head = empty(f"{name}.head", (0, -0.15, 2.25), body)
    sphere(f"{name}.headmesh", 0.66, (0, 0, 0), (1.08, 0.95, 0.9), m_fur, head)
    sphere(f"{name}.muzzle", 0.36, (0, -0.48, -0.15), (1.15, 0.85, 0.75), m_tan, head)
    sphere(f"{name}.nose", 0.11, (0, -0.8, -0.02), (1.3, 0.9, 0.8), m_nose, head)
    # 四角い前歯2本
    for x in (0.065, -0.065):
        bpy.ops.mesh.primitive_cube_add(size=1)
        t = bpy.context.active_object
        t.name = f"{name}.tooth"
        t.scale = (0.11, 0.05, 0.2)
        t.location = (x, -0.76, -0.38)
        t.parent = head
        bv = t.modifiers.new("bev", "BEVEL"); bv.width = 0.02; bv.segments = 3
        t.data.materials.append(m_teeth)
    _smile(f"{name}.mouth", m_mouth, head, (0, -0.73, -0.27), width=0.15, thick=0.018)
    # 小さめの真剣な目
    for side, x in (("L", 0.24), ("R", -0.24)):
        pivot, _, lids = _eye(name, side, (x, -0.47, 0.17), 0.09, DARK_EYE, m_fur, head)
        pivot.rotation_euler = (0, 0, math.radians(-20 if x > 0 else 20))
        for lid in lids:  # 上まぶたを少し下げて「真剣」な目に
            if "up" in lid.name:
                lid.rotation_euler.x = math.radians(-40)
        # 太いもじゃもじゃ灰色まゆ毛
        br = capsule(f"{name}.brow_{side}", 0.07, 0.34, (x * 1.1, -0.52, 0.33),
                     (0, math.radians(90), math.radians(-12 if x > 0 else 12)), m_brow, head)
        br.scale = (1.2, 0.9, br.scale[2])
        nz = br.modifiers.new("fuzz", "DISPLACE")
        tex = bpy.data.textures.new("browfuzz", "CLOUDS"); tex.noise_scale = 0.05
        nz.texture = tex; nz.strength = 0.025
        # 耳
        sphere(f"{name}.ear_{side}", 0.13, (x * 1.9, 0.0, 0.42), (1, 0.6, 1), m_fur, head)
    # 右耳のうしろの小枝（目じるし）
    twig = capsule(f"{name}.twig", 0.025, 0.5, (-0.5, 0.05, 0.42), (math.radians(20), math.radians(70), 0), m_twig, head)
    # 腕・足
    for side, x in (("L", 1), ("R", -1)):
        arm = empty(f"{name}.arm_{side}", (x * 0.95, -0.35, 1.75), body)
        capsule(f"{name}.armmesh_{side}", 0.18, 0.9, (0, 0, -0.38), (0, 0, 0), m_fur, arm)
        arm.rotation_euler = (math.radians(-15), math.radians(x * 25), 0)
        sphere(f"{name}.foot_{side}", 0.22, (x * 0.5, -0.45, 0.1), (1, 1.5, 0.5), m_fur, body)
    # 平たいオール型のしっぽ
    tail = empty(f"{name}.tail", (0, 0.7, 0.2), body)
    sphere(f"{name}.tailmesh", 0.5, (0, 0.5, 0), (0.75, 1.1, 0.12), mat_tail("don_tail"), tail)
    tail.rotation_euler = (math.radians(-12), 0, 0)
    root["parts"] = {"body": body.name, "head": head.name, "twig": twig.name, "tail": tail.name}
    return root
