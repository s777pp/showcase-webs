"""Build an editable Showcase Maker mascot starter model in Blender.

Run with Blender, not system Python:
    blender --background --python scripts/build_mascot_blender.py

The generated model is a deliberately clean, low-complexity modelling base.  It
uses separate named objects and rigid bone parenting so every part can be
replaced, sculpted, joined or weight-painted without reverse engineering a
single opaque mesh.
"""

from __future__ import annotations

import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "mascot-vrm"
BLEND_PATH = OUT_DIR / "showcase-maker-mascot-base.blend"
GLB_PATH = OUT_DIR / "showcase-maker-mascot-base.glb"
PREVIEW_PATH = OUT_DIR / "showcase-maker-mascot-preview.png"
TURNAROUND = OUT_DIR / "turnaround-v1.png"
FACE_SHEET = OUT_DIR / "face-expressions-v1.png"


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.armatures,
                       bpy.data.cameras, bpy.data.lights, bpy.data.materials):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)


def collection(name: str, parent=None):
    col = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(col)
    return col


def move_to_collection(obj, col):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    col.objects.link(obj)


def mat(name, color, metallic=0.0, roughness=0.5, emission=None, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, alpha)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1)
        bsdf.inputs["Emission Strength"].default_value = 1.6
    if alpha < 1:
        bsdf.inputs["Alpha"].default_value = alpha
        m.surface_render_method = "DITHERED"
    return m


def smooth(obj):
    if obj.type == "MESH":
        for p in obj.data.polygons:
            p.use_smooth = True
    return obj


def assign(obj, material):
    if obj.data and hasattr(obj.data, "materials"):
        obj.data.materials.append(material)
    return obj


def uv(name, loc, scale, material, col, segments=32, rings=20):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments, ring_count=rings, location=loc
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    smooth(obj)
    assign(obj, material)
    move_to_collection(obj, col)
    return obj


def cube(name, loc, scale, material, col, bevel=0.04, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = obj.modifiers.new("Soft tailoring", "BEVEL")
        mod.width = bevel
        mod.segments = 3
    assign(obj, material)
    move_to_collection(obj, col)
    return obj


def cyl(name, a, b, radius, material, col, vertices=24, radius2=None):
    a, b = Vector(a), Vector(b)
    delta = b - a
    mid = (a + b) / 2
    bpy.ops.mesh.primitive_cone_add(
        vertices=vertices,
        radius1=radius2 if radius2 is not None else radius,
        radius2=radius,
        depth=delta.length,
        location=mid,
    )
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = delta.to_track_quat("Z", "Y")
    smooth(obj)
    assign(obj, material)
    move_to_collection(obj, col)
    return obj


def curve(name, points, radius, material, col, cyclic=False):
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.resolution_u = 2
    data.bevel_depth = radius
    data.bevel_resolution = 3
    spline = data.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for bp, co in zip(spline.bezier_points, points):
        bp.co = co
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, data)
    col.objects.link(obj)
    assign(obj, material)
    return obj


def parent_bone(obj, rig, bone):
    world = obj.matrix_world.copy()
    obj.parent = rig
    obj.parent_type = "BONE"
    obj.parent_bone = bone
    obj.matrix_world = world


def create_rig(col):
    arm = bpy.data.armatures.new("SM_Mascot_Armature")
    rig = bpy.data.objects.new("SM_Mascot_Rig", arm)
    col.objects.link(rig)
    rig.show_in_front = True
    rig.display_type = "WIRE"
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")

    def eb(name, head, tail, parent=None, connected=False):
        b = arm.edit_bones.new(name)
        b.head, b.tail = head, tail
        if parent:
            b.parent = arm.edit_bones[parent]
            b.use_connect = connected
        return b

    eb("root", (0, 0, 0), (0, 0, 0.12))
    eb("hips", (0, 0, 0.86), (0, 0, 1.02), "root")
    eb("spine", (0, 0, 1.02), (0, 0, 1.22), "hips", True)
    eb("chest", (0, 0, 1.22), (0, 0, 1.43), "spine", True)
    eb("neck", (0, 0, 1.43), (0, 0, 1.52), "chest", True)
    eb("head", (0, 0, 1.52), (0, 0, 1.72), "neck", True)
    eb("eye.L", (0.044, -0.075, 1.655), (0.044, -0.145, 1.655), "head")
    eb("eye.R", (-0.044, -0.075, 1.655), (-0.044, -0.145, 1.655), "head")
    eb("ponytail.01", (0, 0.075, 1.78), (0, 0.10, 1.60), "head")
    eb("ponytail.02", (0, 0.10, 1.60), (0, 0.12, 1.38), "ponytail.01", True)
    eb("ponytail.03", (0, 0.12, 1.38), (0, 0.10, 1.18), "ponytail.02", True)

    for side, sign in (("L", 1), ("R", -1)):
        eb(f"clavicle.{side}", (0, 0, 1.40), (0.16 * sign, 0, 1.40), "chest")
        eb(f"upper_arm.{side}", (0.16 * sign, 0, 1.40), (0.43 * sign, 0, 1.30), f"clavicle.{side}", True)
        eb(f"forearm.{side}", (0.43 * sign, 0, 1.30), (0.67 * sign, 0, 1.20), f"upper_arm.{side}", True)
        eb(f"hand.{side}", (0.67 * sign, 0, 1.20), (0.79 * sign, -0.005, 1.16), f"forearm.{side}", True)
        eb(f"thigh.{side}", (0.095 * sign, 0, 0.92), (0.11 * sign, 0, 0.54), "hips")
        eb(f"shin.{side}", (0.11 * sign, 0, 0.54), (0.105 * sign, 0, 0.14), f"thigh.{side}", True)
        eb(f"foot.{side}", (0.105 * sign, 0, 0.14), (0.105 * sign, -0.16, 0.08), f"shin.{side}", True)

    bpy.ops.object.mode_set(mode="POSE")
    for name in ("eye.L", "eye.R"):
        p = rig.pose.bones[name]
        p.rotation_mode = "XYZ"
        for index, prop, factor in ((0, "look_y", 0.22), (2, "look_x", -0.32)):
            driver = p.driver_add("rotation_euler", index).driver
            driver.expression = f"v*{factor}"
            var = driver.variables.new()
            var.name = "v"
            var.type = "SINGLE_PROP"
            var.targets[0].id = rig
            var.targets[0].data_path = f'["{prop}"]'
    bpy.ops.object.mode_set(mode="OBJECT")

    rig["look_x"] = 0.0
    rig["look_y"] = 0.0
    rig["blink"] = 0.0
    rig["smile"] = 0.0
    for key in ("look_x", "look_y"):
        ui = rig.id_properties_ui(key)
        ui.update(min=-1.0, max=1.0, soft_min=-1.0, soft_max=1.0)
    for key in ("blink", "smile"):
        ui = rig.id_properties_ui(key)
        ui.update(min=0.0, max=1.0, soft_min=0.0, soft_max=1.0)
    return rig


def blink_driver(obj, rig, base_z):
    driver = obj.driver_add("scale", 2).driver
    driver.expression = f"{base_z:.6f}*(1-0.92*b)"
    var = driver.variables.new()
    var.name = "b"
    var.type = "SINGLE_PROP"
    var.targets[0].id = rig
    var.targets[0].data_path = '["blink"]'


def scale_driver(obj, rig, prop, expression):
    for idx in range(3):
        driver = obj.driver_add("scale", idx).driver
        driver.expression = expression
        var = driver.variables.new()
        var.name = prop
        var.type = "SINGLE_PROP"
        var.targets[0].id = rig
        var.targets[0].data_path = f'["{prop}"]'


def make_character():
    clear_scene()
    master = collection("SM_Mascot")
    rig_col = collection("01_Rig", master)
    body_col = collection("02_Body", master)
    face_col = collection("03_Face", master)
    hair_col = collection("04_Hair", master)
    outfit_col = collection("05_Outfit", master)
    accents_col = collection("06_Accents", master)
    ref_col = collection("99_References", master)
    rig = create_rig(rig_col)

    skin = mat("MAT_Skin", (0.98, 0.70, 0.62), roughness=0.62)
    skin_blush = mat("MAT_Skin_Blush", (1.0, 0.46, 0.52), roughness=0.7)
    white = mat("MAT_Eye_White", (0.95, 0.98, 1.0), roughness=0.35)
    iris = mat("MAT_Iris_Cyan", (0.02, 0.45, 1.0), roughness=0.25, emission=(0.0, 0.16, 0.5))
    pupil = mat("MAT_Pupil", (0.002, 0.006, 0.014), roughness=0.3)
    lash = mat("MAT_Lashes", (0.008, 0.01, 0.03), roughness=0.5)
    hair = mat("MAT_Hair_Navy", (0.012, 0.018, 0.06), metallic=0.08, roughness=0.32)
    hair_blue = mat("MAT_Hair_Cyan_Strands", (0.0, 0.28, 0.90), roughness=0.28, emission=(0.0, 0.08, 0.35))
    black = mat("MAT_Cloth_Black", (0.008, 0.012, 0.022), roughness=0.55)
    black_soft = mat("MAT_Cloth_Soft", (0.022, 0.028, 0.045), roughness=0.7)
    cyan = mat("MAT_Showcase_Cyan", (0.0, 0.58, 0.93), metallic=0.12, roughness=0.25, emission=(0.0, 0.11, 0.32))
    metal = mat("MAT_Metal", (0.15, 0.18, 0.23), metallic=0.9, roughness=0.2)
    stocking = mat("MAT_Stockings", (0.025, 0.018, 0.040), roughness=0.68, alpha=0.82)

    # Body volumes. Clothes hide most segment seams while keeping the starter editable.
    torso = uv("BODY_Torso", (0, 0, 1.245), (0.165, 0.105, 0.245), skin, body_col)
    hips = uv("BODY_Hips", (0, 0, 0.91), (0.18, 0.12, 0.16), skin, body_col)
    neck = cyl("BODY_Neck", (0, 0, 1.42), (0, 0, 1.53), 0.047, skin, body_col)
    head = uv("BODY_Head", (0, -0.004, 1.655), (0.122, 0.105, 0.145), skin, body_col, 40, 28)
    parent_bone(torso, rig, "spine")
    parent_bone(hips, rig, "hips")
    parent_bone(neck, rig, "neck")
    parent_bone(head, rig, "head")

    for side, sign in (("L", 1), ("R", -1)):
        upper = cyl(f"BODY_UpperArm_{side}", (0.16*sign,0,1.40), (0.43*sign,0,1.30), 0.055, skin, body_col, radius2=0.047)
        fore = cyl(f"BODY_Forearm_{side}", (0.43*sign,0,1.30), (0.67*sign,0,1.20), 0.047, skin, body_col, radius2=0.035)
        hand = uv(f"BODY_Hand_{side}", (0.72*sign,-0.002,1.18), (0.035,0.026,0.068), skin, body_col)
        thigh = cyl(f"BODY_Thigh_{side}", (0.095*sign,0,0.92), (0.11*sign,0,0.54), 0.095, skin, body_col, radius2=0.072)
        shin = cyl(f"BODY_Shin_{side}", (0.11*sign,0,0.54), (0.105*sign,0,0.14), 0.071, skin, body_col, radius2=0.045)
        parent_bone(upper, rig, f"upper_arm.{side}")
        parent_bone(fore, rig, f"forearm.{side}")
        parent_bone(hand, rig, f"hand.{side}")
        parent_bone(thigh, rig, f"thigh.{side}")
        parent_bone(shin, rig, f"shin.{side}")

    # Eyes face -Y. Separate eye bones are already driven by rig look properties.
    for side, x, bone in (("L", 0.044, "eye.L"), ("R", -0.044, "eye.R")):
        eye = uv(f"FACE_EyeWhite_{side}", (x,-0.095,1.66), (0.039,0.014,0.026), white, face_col, 32, 16)
        ir = uv(f"FACE_Iris_{side}", (x,-0.108,1.66), (0.018,0.008,0.020), iris, face_col, 28, 14)
        pu = uv(f"FACE_Pupil_{side}", (x,-0.115,1.66), (0.007,0.004,0.011), pupil, face_col, 20, 12)
        for obj in (eye, ir, pu):
            base_z = obj.scale.z
            parent_bone(obj, rig, bone)
            blink_driver(obj, rig, base_z)
        lash_curve = curve(
            f"FACE_UpperLash_{side}",
            [(x-0.04,-0.119,1.662),(x,-0.124,1.686),(x+0.04,-0.119,1.663)],
            0.004, lash, face_col,
        )
        parent_bone(lash_curve, rig, "head")

    brow_l = curve("FACE_Brow_L", [(0.006,-0.112,1.712),(0.045,-0.116,1.723),(0.080,-0.108,1.714)], 0.004, hair, face_col)
    brow_r = curve("FACE_Brow_R", [(-0.006,-0.112,1.712),(-0.045,-0.116,1.723),(-0.080,-0.108,1.714)], 0.004, hair, face_col)
    nose = curve("FACE_Nose", [(0,-0.119,1.653),(0.006,-0.126,1.636),(0,-0.128,1.632)], 0.002, skin_blush, face_col)
    mouth_neutral = curve("FACE_Mouth_Neutral", [(-0.026,-0.120,1.606),(0,-0.126,1.601),(0.026,-0.120,1.606)], 0.003, skin_blush, face_col)
    mouth_smile = curve("FACE_Mouth_Smile", [(-0.030,-0.121,1.607),(0,-0.128,1.591),(0.030,-0.121,1.607)], 0.0035, skin_blush, face_col)
    for obj in (brow_l,brow_r,nose,mouth_neutral,mouth_smile):
        parent_bone(obj, rig, "head")
    scale_driver(mouth_neutral, rig, "smile", "1-0.95*smile")
    scale_driver(mouth_smile, rig, "smile", "0.02+0.98*smile")

    # Hair cap, bangs, side locks and ponytail.
    cap = uv("HAIR_Cap", (0,0.015,1.723), (0.128,0.11,0.105), hair, hair_col, 40, 24)
    parent_bone(cap, rig, "head")
    bang_specs = [
        (-0.075,-0.095,1.76,-0.060,-0.125,1.61),
        (-0.040,-0.110,1.78,-0.025,-0.132,1.60),
        (0.000,-0.112,1.79,0.018,-0.134,1.61),
        (0.042,-0.105,1.78,0.060,-0.126,1.625),
        (0.076,-0.088,1.755,0.088,-0.112,1.64),
    ]
    for i,(x1,y1,z1,x2,y2,z2) in enumerate(bang_specs,1):
        obj = curve(f"HAIR_Bang_{i:02}", [(x1,y1,z1),((x1+x2)/2,y2-0.005,(z1+z2)/2),(x2,y2,z2)], 0.012 if i in (2,3) else 0.010, hair, hair_col)
        parent_bone(obj, rig, "head")
    for side, sign in (("L",1),("R",-1)):
        lock = curve(f"HAIR_SideLock_{side}", [(0.10*sign,-0.02,1.73),(0.13*sign,-0.03,1.56),(0.12*sign,0,1.38)], 0.013, hair, hair_col)
        accent = curve(f"HAIR_Accent_{side}", [(0.082*sign,-0.035,1.77),(0.11*sign,-0.05,1.59),(0.105*sign,-0.01,1.43)], 0.0045, hair_blue, hair_col)
        parent_bone(lock, rig, "head")
        parent_bone(accent, rig, "head")
    tie = uv("HAIR_PonytailTie", (0,0.10,1.78), (0.052,0.045,0.038), cyan, hair_col)
    parent_bone(tie, rig, "head")
    for i, x in enumerate((-0.07,-0.035,0,0.035,0.07),1):
        strand = curve(f"HAIR_Ponytail_{i:02}", [(x*0.4,0.095,1.79),(x,0.12,1.58),(x*1.15,0.10,1.35),(x*0.8,0.07,1.15)], 0.018 if i==3 else 0.014, hair if i%2 else hair_blue, hair_col)
        parent_bone(strand, rig, "ponytail.01")

    # Cropped top and shorts.
    top = uv("OUTFIT_RibbedCropTop", (0,-0.006,1.285), (0.172,0.112,0.185), black, outfit_col)
    top.scale.z = 0.88
    parent_bone(top, rig, "chest")
    waist = cyl("OUTFIT_WaistBand", (0,0,1.065), (0,0,1.115), 0.165, black_soft, outfit_col, vertices=36)
    shorts = cube("OUTFIT_Shorts", (0,0,0.93), (0.18,0.12,0.12), black_soft, outfit_col, bevel=0.055)
    parent_bone(waist, rig, "spine")
    parent_bone(shorts, rig, "hips")
    for side, sign in (("L",1),("R",-1)):
        stocking_obj = cyl(f"OUTFIT_Stocking_{side}", (0.105*sign,0,0.77), (0.105*sign,0,0.14), 0.091, stocking, outfit_col, radius2=0.046)
        shoe = cube(f"OUTFIT_Sneaker_{side}", (0.105*sign,-0.075,0.075), (0.072,0.15,0.065), black, outfit_col, bevel=0.035)
        sole = cube(f"OUTFIT_Sole_{side}", (0.105*sign,-0.08,0.027), (0.078,0.157,0.022), cyan, accents_col, bevel=0.018)
        parent_bone(stocking_obj, rig, f"thigh.{side}")
        parent_bone(shoe, rig, f"foot.{side}")
        parent_bone(sole, rig, f"foot.{side}")

    # Crossed chest straps and belt hardware.
    for i,(a,b) in enumerate((
        ((-0.13,-0.118,1.42),(0.075,-0.123,1.16)),
        ((0.13,-0.118,1.42),(-0.075,-0.123,1.16)),
    ),1):
        strap = cyl(f"OUTFIT_ChestStrap_{i}", a,b,0.014,black_soft,outfit_col,vertices=12)
        parent_bone(strap, rig, "chest")
    belt = cyl("OUTFIT_Belt", (0,0,0.99),(0,0,1.025),0.185,black,outfit_col,vertices=36)
    buckle = cube("OUTFIT_BeltBuckle", (0,-0.128,1.008), (0.034,0.012,0.029), metal, accents_col, bevel=0.006)
    parent_bone(belt, rig, "hips")
    parent_bone(buckle, rig, "hips")

    # Oversized dropped-shoulder jacket: body panels and puffy sleeves.
    left_panel = cube("OUTFIT_JacketPanel_L", (0.185,0.055,1.20), (0.10,0.075,0.255), black_soft, outfit_col, bevel=0.055, rotation=(0,0,-0.13))
    right_panel = cube("OUTFIT_JacketPanel_R", (-0.185,0.055,1.20), (0.10,0.075,0.255), black_soft, outfit_col, bevel=0.055, rotation=(0,0,0.13))
    back_panel = cube("OUTFIT_JacketBack", (0,0.11,1.24), (0.22,0.06,0.24), black_soft, outfit_col, bevel=0.055)
    for obj in (left_panel,right_panel,back_panel):
        parent_bone(obj, rig, "chest")
    for side, sign in (("L",1),("R",-1)):
        sleeve_u = cyl(f"OUTFIT_JacketSleeveUpper_{side}", (0.14*sign,0.01,1.37),(0.43*sign,0.005,1.30),0.105,black_soft,outfit_col,vertices=28,radius2=0.085)
        sleeve_f = cyl(f"OUTFIT_JacketSleeveFore_{side}", (0.43*sign,0.005,1.30),(0.66*sign,0,1.20),0.085,black_soft,outfit_col,vertices=28,radius2=0.058)
        cuff = cyl(f"OUTFIT_JacketCuff_{side}", (0.62*sign,0,1.22),(0.69*sign,0,1.19),0.062,black,outfit_col,vertices=24)
        lining = curve(f"ACCENT_JacketLining_{side}", [(0.12*sign,-0.085,1.42),(0.24*sign,-0.095,1.29),(0.20*sign,-0.09,1.05)],0.012,cyan,accents_col)
        parent_bone(sleeve_u, rig, f"upper_arm.{side}")
        parent_bone(sleeve_f, rig, f"forearm.{side}")
        parent_bone(cuff, rig, f"forearm.{side}")
        parent_bone(lining, rig, "chest")

    choker = cyl("ACCENT_Choker", (0,0,1.485),(0,0,1.515),0.064,black,accents_col,vertices=32)
    pendant = cube("ACCENT_TrianglePendant", (0,-0.074,1.445), (0.022,0.008,0.026), cyan, accents_col, bevel=0.005, rotation=(0,0,math.radians(45)))
    parent_bone(choker, rig, "neck")
    parent_bone(pendant, rig, "neck")
    for side, sign in (("L",1),("R",-1)):
        earring = cube(f"ACCENT_Earring_{side}",(0.115*sign,-0.018,1.61),(0.011,0.006,0.025),cyan,accents_col,bevel=0.004,rotation=(0,0,math.radians(45)))
        parent_bone(earring, rig, "head")

    # Embedded references: initially hidden, available from the Outliner/Image Editor.
    for label, path, x in (("REF_Turnaround",TURNAROUND,-3.2),("REF_FaceExpressions",FACE_SHEET,3.2)):
        if path.exists():
            image = bpy.data.images.load(str(path), check_existing=True)
            image.pack()
            empty = bpy.data.objects.new(label, None)
            empty.empty_display_type = "IMAGE"
            empty.data = image
            empty.location = (x,0.55,1.0)
            empty.rotation_euler = (math.radians(90),0,0)
            empty.empty_display_size = 2.4
            empty.hide_render = True
            empty.hide_viewport = True
            ref_col.objects.link(empty)

    # Useful selection groups and metadata.
    rig["author"] = "Showcase Maker / n1t1337"
    rig["model_status"] = "Editable Blender starter; retopology and final weight painting recommended"
    rig["reference_front"] = "approved-concept.png"
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    return rig


def setup_scene(rig):
    scene = bpy.context.scene
    # Blender 5.x exposes the current Eevee engine under the legacy enum name.
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(PREVIEW_PATH)
    scene.render.film_transparent = False
    scene.world.color = (0.005,0.009,0.016)

    bpy.ops.object.camera_add(location=(0,-4.4,1.28))
    cam = bpy.context.object
    cam.name = "CAM_WebHeroPreview"
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 1.95
    cam.rotation_euler = (math.radians(90),0,0)
    # Aim the camera exactly at the character centre.
    direction = Vector((0,0,1.02)) - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z","Y").to_euler()
    scene.camera = cam

    def light(name, loc, energy, color, size):
        data = bpy.data.lights.new(name,"AREA")
        data.energy = energy
        data.color = color
        data.shape = "DISK"
        data.size = size
        obj = bpy.data.objects.new(name,data)
        scene.collection.objects.link(obj)
        obj.location = loc
        obj.rotation_euler = (Vector((0,0,1.15))-obj.location).to_track_quat("-Z","Y").to_euler()
        return obj
    light("KEY_Cyan",(-2.0,-2.5,2.8),850,(0.35,0.82,1.0),3.0)
    light("FILL_Soft",(2.5,-1.0,2.0),650,(0.75,0.85,1.0),2.5)
    light("RIM_Blue",(0,2.0,2.3),1000,(0.05,0.25,1.0),2.0)
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0,0,-0.005))
    floor = bpy.context.object
    floor.name = "PREVIEW_Floor"
    assign(floor, mat("MAT_PreviewFloor",(0.006,0.014,0.025),roughness=0.8))

    scene["README"] = "Select SM_Mascot_Rig and edit custom properties look_x, look_y, blink and smile. References are packed and hidden in 99_References."
    scene["web_camera_note"] = "Website framing should crop around mid-thigh and preserve head/ponytail."


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rig = make_character()
    setup_scene(rig)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), compress=True)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=str(GLB_PATH),
        export_format="GLB",
        use_selection=False,
        export_apply=True,
        export_yup=True,
    )
    bpy.ops.render.render(write_still=True)
    # Save again so the final file remembers the completed render and active rig.
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), compress=True)
    print(f"BLEND={BLEND_PATH}")
    print(f"GLB={GLB_PATH}")
    print(f"PREVIEW={PREVIEW_PATH}")


if __name__ == "__main__":
    main()
