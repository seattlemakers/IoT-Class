import FreeCAD as App
import PartDesign
import Import

doc = App.newDocument("ESP32_LD2410_Clamshell")

# -----------------------------------------------------------------------------
# 1. NATIVE PARAMETER SET (App::VarSet)
# -----------------------------------------------------------------------------
params = doc.addObject("App::VarSet", "Params")

param_defs = [
    # Clamshell Enclosure Z-Stack (Total Z = 35.5mm: 17.5mm Base + 18.0mm Lid)
    ("Wall", 2.0, "Enclosure"),
    ("Floor", 2.0, "Enclosure"),
    ("LidRoof", 2.5, "Enclosure"),
    ("IntX", 63.0, "Enclosure"),
    ("IntY", 56.0, "Enclosure"),
    ("IntZ", 31.0, "Enclosure"),
    ("BaseWallH", 15.5, "Enclosure"),    # Base outer wall Z = 2.0 + 15.5 = 17.5mm
    ("LipH", 2.0, "Enclosure"),          # Perimeter nesting tongue height
    ("LipClearXY", 0.15, "Enclosure"),   # Radial clearance between tongue and groove
    ("LipClearZ", 0.20, "Enclosure"),    # Axial clearance in groove
    ("LidOuterLipW", 0.95, "Enclosure"), # 2 perimeters on Lid outer skirt
    # Concentric Corners & #4 x 5/8" (15.9mm) Screw Bosses
    ("CornerR", 4.10, "Fasteners"),      # Outer corner radius & boss center (4.1, 4.1)
    ("BaseBossR", 3.00, "Fasteners"),    # 6.0mm OD boss (tangent to 1.10mm lip inset)
    ("LidBossH", 8.0, "Fasteners"),      # Upper 8.0mm in Lid leaves 7.7mm screw thread in Base
    ("BossGapZ", 0.20, "Fasteners"),     # Ensures perimeter seam clamps before bosses bottom out
    ("PilotD", 2.4, "Fasteners"),
    ("ClearanceD", 3.2, "Fasteners"),
    ("CsinkD", 5.6, "Fasteners"),
    ("PilotDepth", 9.5, "Fasteners"),
    # ESP32-S (Variant A: 25.8 x 48.1 x 1.2 mm)
    ("EspW", 25.8, "ESP32"),
    ("EspL", 48.1, "ESP32"),
    ("EspThick", 1.2, "ESP32"),
    ("EspClear", 0.15, "ESP32"),
    ("EspShelfH", 5.0, "ESP32"),
    ("EspLipW", 1.5, "ESP32"),
    ("EspEndStopL", 1.5, "ESP32"),
    ("EspInnerReach", 3.65, "ESP32"),
    ("EspTroughOuter", 0.32, "ESP32"),
    ("EspTroughW", 2.30, "ESP32"),
    ("EspTroughDepth", 2.20, "ESP32"),
    ("EspBtnNotchL", 12.0, "ESP32"),
    ("UsbW", 12.0, "ESP32"),
    ("UsbH", 7.0, "ESP32"),
    # LD2410C (22.0 header edge x 16.0 depth x 1.7 mm)
    ("LdW", 22.3, "LD2410"),
    ("LdL", 16.3, "LD2410"),
    ("LdLipH", 1.7, "LD2410"),
    ("LdLipW", 1.5, "LD2410"),
    ("LdWingW", 4.25, "LD2410"),
]

for name, val, group in param_defs:
    params.addProperty("App::PropertyLength", name, group)
    setattr(params, name, val)


def add_pd_feature(body, xy_plane, type_id, name, pos_exprs, prop_exprs, refine=False):
    """Create a PartDesign feature attached to the Body XY_Plane with expressions."""
    feat = body.newObject(type_id, name)
    feat.AttachmentSupport = [(xy_plane, "")]
    feat.MapMode = "FlatFace"
    for axis, expr in pos_exprs.items():
        feat.setExpression(f".AttachmentOffset.Base.{axis}", expr)
    for prop, expr in prop_exprs.items():
        feat.setExpression(prop, expr)
    if hasattr(feat, "Refine"):
        feat.Refine = refine
    return feat


assembly = doc.addObject("App::Part", "EnclosureAssembly")

ox_expr = "(Params.IntX + 2 * Params.Wall)"
oy_expr = "(Params.IntY + 2 * Params.Wall)"
cr_expr = "Params.CornerR"
lip_inset = "(Params.LidOuterLipW + Params.LipClearXY)"  # 1.10mm inset from outer face
base_split_z = "(Params.Floor + Params.BaseWallH)"       # 17.5mm
base_lip_top_z = f"({base_split_z} + Params.LipH)"       # 19.5mm
base_boss_top_z = "(Params.Floor + Params.IntZ + Params.LidRoof - Params.LidBossH - Params.BossGapZ)"  # 27.3mm

boss_positions = [
    ("SW", cr_expr, cr_expr),
    ("SE", f"{ox_expr} - {cr_expr}", cr_expr),
    ("NE", f"{ox_expr} - {cr_expr}", f"{oy_expr} - {cr_expr}"),
    ("NW", cr_expr, f"{oy_expr} - {cr_expr}"),
]

# -----------------------------------------------------------------------------
# 2. BASE BODY (17.5mm Walls, 19.5mm Inner Nesting Lip, 27.3mm Protruding Bosses)
# -----------------------------------------------------------------------------
base_body = doc.addObject("PartDesign::Body", "Base")
assembly.addObject(base_body)
base_xy = next(f for f in base_body.Origin.OriginFeatures if f.Role == "XY_Plane")

# Outer Shell up to Split Line (Z = 17.5mm)
add_pd_feature(
    base_body, base_xy, "PartDesign::AdditiveBox", "OuterShell_X",
    {"x": cr_expr, "y": "0", "z": "0"},
    {"Length": f"{ox_expr} - 2 * {cr_expr}", "Width": oy_expr, "Height": base_split_z}
)
add_pd_feature(
    base_body, base_xy, "PartDesign::AdditiveBox", "OuterShell_Y",
    {"x": "0", "y": cr_expr, "z": "0"},
    {"Length": ox_expr, "Width": f"{oy_expr} - 2 * {cr_expr}", "Height": base_split_z}
)
for tag, bx_expr, by_expr in boss_positions:
    add_pd_feature(
        base_body, base_xy, "PartDesign::AdditiveCylinder", f"OuterCorner_{tag}",
        {"x": bx_expr, "y": by_expr, "z": "0"},
        {"Radius": cr_expr, "Height": base_split_z}
    )

# Inner Nesting Tongue Shell up to Z = 19.5mm (Inset by 1.10mm)
add_pd_feature(
    base_body, base_xy, "PartDesign::AdditiveBox", "LipShell_X",
    {"x": cr_expr, "y": lip_inset, "z": "0"},
    {
        "Length": f"{ox_expr} - 2 * {cr_expr}",
        "Width": f"{oy_expr} - 2 * {lip_inset}",
        "Height": base_lip_top_z,
    }
)
add_pd_feature(
    base_body, base_xy, "PartDesign::AdditiveBox", "LipShell_Y",
    {"x": lip_inset, "y": cr_expr, "z": "0"},
    {
        "Length": f"{ox_expr} - 2 * {lip_inset}",
        "Width": f"{oy_expr} - 2 * {cr_expr}",
        "Height": base_lip_top_z,
    }
)

# Inner Cavity Cut (Leaves 2.0mm lower wall and 0.90mm x 2.0mm upper tongue)
add_pd_feature(
    base_body, base_xy, "PartDesign::SubtractiveBox", "InnerCavity",
    {"x": "Params.Wall", "y": "Params.Wall", "z": "Params.Floor"},
    {"Length": "Params.IntX", "Width": "Params.IntY", "Height": "Params.IntZ + 1 mm"}
)

# 4x Protruding Corner Bosses (Z = 0 to 27.3mm) & Pilot Holes
for tag, bx_expr, by_expr in boss_positions:
    add_pd_feature(
        base_body, base_xy, "PartDesign::AdditiveCylinder", f"Boss_{tag}",
        {"x": bx_expr, "y": by_expr, "z": "0"},
        {"Radius": "Params.BaseBossR", "Height": base_boss_top_z}
    )
    add_pd_feature(
        base_body, base_xy, "PartDesign::SubtractiveCylinder", f"Pilot_{tag}",
        {"x": bx_expr, "y": by_expr, "z": f"{base_boss_top_z} - Params.PilotDepth"},
        {"Radius": "Params.PilotD / 2", "Height": "Params.PilotDepth + 1 mm"}
    )

# -----------------------------------------------------------------------------
# 3. ESP32 RAILS (Shifted to X = 7.6mm to Clear (4.1, 4.1) R=3.0mm Bosses)
# -----------------------------------------------------------------------------
esp_x0 = "(Params.CornerR + Params.BaseBossR + 0.5 mm + Params.EspLipW + Params.EspClear)"
esp_rx = f"({esp_x0} + Params.EspW)"
esp_y0 = "(Params.Wall + 0.2 mm)"

rail_total_w = "(Params.EspLipW + Params.EspClear + Params.EspInnerReach)"
rail_total_l = "(Params.EspL + Params.EspEndStopL)"
rail_total_h = "(Params.Floor + Params.EspShelfH + Params.EspThick)"
shelf_z = "(Params.Floor + Params.EspShelfH)"
trough_z = "(Params.Floor + Params.EspShelfH - Params.EspTroughDepth)"
trough_cut_h = "(Params.EspTroughDepth + Params.EspThick + 1 mm)"
notch_w = "(Params.EspInnerReach - Params.EspTroughOuter - Params.EspTroughW + 0.5 mm)"

# Left Rail
add_pd_feature(
    base_body, base_xy, "PartDesign::AdditiveBox", "EspRailL_Block",
    {"x": f"{esp_x0} - Params.EspClear - Params.EspLipW", "y": esp_y0, "z": "0"},
    {"Length": rail_total_w, "Width": rail_total_l, "Height": rail_total_h}
)
add_pd_feature(
    base_body, base_xy, "PartDesign::SubtractiveBox", "EspRailL_ShelfCut",
    {"x": f"{esp_x0} - Params.EspClear", "y": f"{esp_y0} - 0.1 mm", "z": shelf_z},
    {
        "Length": "Params.EspClear + Params.EspInnerReach + 0.5 mm",
        "Width": "Params.EspL + 0.1 mm",
        "Height": "Params.EspThick + 1 mm",
    }
)
add_pd_feature(
    base_body, base_xy, "PartDesign::SubtractiveBox", "EspRailL_Trough",
    {"x": f"{esp_x0} + Params.EspTroughOuter", "y": f"{esp_y0} - 0.1 mm", "z": trough_z},
    {"Length": "Params.EspTroughW", "Width": "Params.EspL + 0.2 mm", "Height": trough_cut_h}
)
add_pd_feature(
    base_body, base_xy, "PartDesign::SubtractiveBox", "EspRailL_BtnNotch",
    {
        "x": f"{esp_x0} + Params.EspTroughOuter + Params.EspTroughW - 0.1 mm",
        "y": f"{esp_y0} - 0.1 mm",
        "z": trough_z,
    },
    {"Length": notch_w, "Width": "Params.EspBtnNotchL", "Height": trough_cut_h}
)

# Right Rail
add_pd_feature(
    base_body, base_xy, "PartDesign::AdditiveBox", "EspRailR_Block",
    {"x": f"{esp_rx} - Params.EspInnerReach", "y": esp_y0, "z": "0"},
    {"Length": rail_total_w, "Width": rail_total_l, "Height": rail_total_h}
)
add_pd_feature(
    base_body, base_xy, "PartDesign::SubtractiveBox", "EspRailR_ShelfCut",
    {"x": f"{esp_rx} - Params.EspInnerReach - 0.5 mm", "y": f"{esp_y0} - 0.1 mm", "z": shelf_z},
    {
        "Length": "Params.EspInnerReach + Params.EspClear + 0.5 mm",
        "Width": "Params.EspL + 0.1 mm",
        "Height": "Params.EspThick + 1 mm",
    }
)
add_pd_feature(
    base_body, base_xy, "PartDesign::SubtractiveBox", "EspRailR_Trough",
    {
        "x": f"{esp_rx} - Params.EspTroughOuter - Params.EspTroughW",
        "y": f"{esp_y0} - 0.1 mm",
        "z": trough_z,
    },
    {"Length": "Params.EspTroughW", "Width": "Params.EspL + 0.2 mm", "Height": trough_cut_h}
)
add_pd_feature(
    base_body, base_xy, "PartDesign::SubtractiveBox", "EspRailR_BtnNotch",
    {"x": f"{esp_rx} - Params.EspInnerReach - 0.4 mm", "y": f"{esp_y0} - 0.1 mm", "z": trough_z},
    {"Length": notch_w, "Width": "Params.EspBtnNotchL", "Height": trough_cut_h}
)

# USB-C Cutout (Z = 2.0 to 9.0mm, leaving 8.5mm solid bridge below split line)
add_pd_feature(
    base_body, base_xy, "PartDesign::SubtractiveBox", "UsbCutout",
    {"x": f"{esp_x0} + (Params.EspW - Params.UsbW) / 2", "y": "-1 mm", "z": "Params.Floor"},
    {"Length": "Params.UsbW", "Width": "Params.Wall + 2 mm", "Height": "Params.UsbH"}
)

# -----------------------------------------------------------------------------
# 4. LD2410C CRADLE
# -----------------------------------------------------------------------------
ld_ox0 = f"({ox_expr} - Params.Wall - Params.LdL - Params.LdLipW - 4 mm)"
ld_oy0 = f"(Params.Wall + (Params.IntY - Params.LdW - 2 * Params.LdLipW) / 2)"

add_pd_feature(
    base_body, base_xy, "PartDesign::AdditiveBox", "LdCradleBlock",
    {"x": ld_ox0, "y": ld_oy0, "z": "0"},
    {
        "Length": "Params.LdL + Params.LdLipW",
        "Width": "Params.LdW + 2 * Params.LdLipW",
        "Height": "Params.Floor + Params.EspShelfH + Params.LdLipH",
    }
)
add_pd_feature(
    base_body, base_xy, "PartDesign::SubtractiveBox", "LdPcbPocket",
    {"x": ld_ox0, "y": f"{ld_oy0} + Params.LdLipW", "z": "Params.Floor + Params.EspShelfH"},
    {"Length": "Params.LdL", "Width": "Params.LdW", "Height": "Params.LdLipH + 1 mm"}
)
add_pd_feature(
    base_body, base_xy, "PartDesign::SubtractiveBox", "LdSolderAndAntennaRelief",
    {"x": f"{ld_ox0} - 0.5 mm", "y": f"{ld_oy0} + Params.LdLipW + Params.LdWingW", "z": "Params.Floor"},
    {
        "Length": "Params.LdL - 1.5 mm + 0.5 mm",
        "Width": "Params.LdW - 2 * Params.LdWingW",
        "Height": "Params.EspShelfH + 1 mm",
    },
    refine=True
)

# -----------------------------------------------------------------------------
# 5. CLAMSHELL LID BODY (18.0mm Tall, Printed Roof-Down on Z = 0)
# -----------------------------------------------------------------------------
lid_body = doc.addObject("PartDesign::Body", "Lid")
assembly.addObject(lid_body)
lid_xy = next(f for f in lid_body.Origin.OriginFeatures if f.Role == "XY_Plane")

lid_h_expr = "(Params.LidRoof + Params.IntZ - Params.BaseWallH)"  # 18.0mm
lid_rabbet_z = f"({lid_h_expr} - Params.LipH - Params.LipClearZ)" # 15.8mm
lid_socket_r = "(Params.CornerR - Params.LidOuterLipW)"           # 3.15mm (0.15mm clearance to 3.0mm Base boss)

# Outer Shell (Z_lid = 0 to 18.0mm)
add_pd_feature(
    lid_body, lid_xy, "PartDesign::AdditiveBox", "LidOuter_X",
    {"x": cr_expr, "y": "0", "z": "0"},
    {"Length": f"{ox_expr} - 2 * {cr_expr}", "Width": oy_expr, "Height": lid_h_expr}
)
add_pd_feature(
    lid_body, lid_xy, "PartDesign::AdditiveBox", "LidOuter_Y",
    {"x": "0", "y": cr_expr, "z": "0"},
    {"Length": ox_expr, "Width": f"{oy_expr} - 2 * {cr_expr}", "Height": lid_h_expr}
)
for tag, bx_expr, by_expr in boss_positions:
    add_pd_feature(
        lid_body, lid_xy, "PartDesign::AdditiveCylinder", f"LidCorner_{tag}",
        {"x": bx_expr, "y": by_expr, "z": "0"},
        {"Radius": cr_expr, "Height": lid_h_expr}
    )

# Main Interior Cavity (Z_lid = 2.5mm to 18.0mm)
add_pd_feature(
    lid_body, lid_xy, "PartDesign::SubtractiveBox", "LidCavity",
    {"x": "Params.Wall", "y": "Params.Wall", "z": "Params.LidRoof"},
    {"Length": "Params.IntX", "Width": "Params.IntY", "Height": lid_h_expr}
)

# Rim Rabbet Groove (Z_lid = 15.8mm to 18.0mm, leaves 0.95mm outer skirt)
add_pd_feature(
    lid_body, lid_xy, "PartDesign::SubtractiveBox", "LidRabbet_X",
    {"x": cr_expr, "y": "Params.LidOuterLipW", "z": lid_rabbet_z},
    {
        "Length": f"{ox_expr} - 2 * {cr_expr}",
        "Width": f"{oy_expr} - 2 * Params.LidOuterLipW",
        "Height": "Params.LipH + Params.LipClearZ + 1 mm",
    }
)
add_pd_feature(
    lid_body, lid_xy, "PartDesign::SubtractiveBox", "LidRabbet_Y",
    {"x": "Params.LidOuterLipW", "y": cr_expr, "z": lid_rabbet_z},
    {
        "Length": f"{ox_expr} - 2 * Params.LidOuterLipW",
        "Width": f"{oy_expr} - 2 * {cr_expr}",
        "Height": "Params.LipH + Params.LipClearZ + 1 mm",
    }
)

# 4x Upper Lid Bosses (Z_lid = 0 to 8.0mm) + Alignment Sockets (Z_lid = 8.0 to 18.0mm)
for idx, (tag, bx_expr, by_expr) in enumerate(boss_positions):
    # Solid upper boss (Z_lid = 0 to 8.0mm)
    add_pd_feature(
        lid_body, lid_xy, "PartDesign::AdditiveCylinder", f"LidBoss_{tag}",
        {"x": bx_expr, "y": by_expr, "z": "0"},
        {"Radius": lid_socket_r, "Height": "Params.LidBossH"}
    )
    # Cylindrical socket for protruding Base boss (Z_lid = 8.0 to 18.0mm)
    add_pd_feature(
        lid_body, lid_xy, "PartDesign::SubtractiveCylinder", f"LidBossSocket_{tag}",
        {"x": bx_expr, "y": by_expr, "z": "Params.LidBossH"},
        {"Radius": lid_socket_r, "Height": lid_h_expr}
    )
    # Through clearance hole (Z_lid = 0 to 8.0mm)
    add_pd_feature(
        lid_body, lid_xy, "PartDesign::SubtractiveCylinder", f"Clearance_{tag}",
        {"x": bx_expr, "y": by_expr, "z": "-0.5 mm"},
        {"Radius": "Params.ClearanceD / 2", "Height": "Params.LidBossH + 1 mm"}
    )
    # 82-deg flat-head countersink on outer face (Z_lid = 0 to 1.38mm, 49-deg bed angle prints support-free)
    add_pd_feature(
        lid_body, lid_xy, "PartDesign::SubtractiveCone", f"Countersink_{tag}",
        {"x": bx_expr, "y": by_expr, "z": "-0.01 mm"},
        {
            "Radius1": "Params.CsinkD / 2",
            "Radius2": "Params.ClearanceD / 2",
            "Height": "(Params.CsinkD - Params.ClearanceD) / (2 * tan(41 deg)) + 0.01 mm",
        },
        refine=(idx == len(boss_positions) - 1)
    )

# Place Lid beside Base, ready to slice flat on Z = 0
lid_body.setExpression(".Placement.Base.x", f"{ox_expr} + 10 mm")

# -----------------------------------------------------------------------------
# 6. RECOMPUTE & EXPORT
# -----------------------------------------------------------------------------
doc.recompute()
Import.export([assembly], "esp32_ld2410_clamshell.step")