import FreeCAD as App
import PartDesign
import Import

doc = App.newDocument("ESP32_LD2410_Enclosure")

# -----------------------------------------------------------------------------
# 1. NATIVE PARAMETER SET (App::VarSet)
# -----------------------------------------------------------------------------
params = doc.addObject("App::VarSet", "Params")

param_defs = [
    # Enclosure
    ("Wall", 2.0, "Enclosure"),
    ("Floor", 2.0, "Enclosure"),
    ("LidThick", 3.0, "Enclosure"),
    ("IntX", 62.0, "Enclosure"),
    ("IntY", 56.0, "Enclosure"),
    ("IntZ", 31.0, "Enclosure"),
    # Fasteners (#4 Flat-Head Wood Screws, Concentric 6.4mm Bosses/Corners)
    ("BossOD", 6.4, "Fasteners"),
    ("PilotD", 2.4, "Fasteners"),
    ("ClearanceD", 3.2, "Fasteners"),
    ("CsinkD", 5.6, "Fasteners"),
    ("ScrewDepth", 14.5, "Fasteners"),
    # ESP32-S (Variant A: 25.8 x 48.1 x 1.2 mm, Component-Side Down)
    ("EspW", 25.8, "ESP32"),
    ("EspL", 48.1, "ESP32"),
    ("EspThick", 1.2, "ESP32"),
    ("EspClear", 0.15, "ESP32"),
    ("EspShelfH", 5.0, "ESP32"),
    ("EspLipW", 1.5, "ESP32"),
    ("EspEndStopL", 1.5, "ESP32"),
    ("EspInnerReach", 3.65, "ESP32"),   # Stops 0.25mm short of 18mm RF shield
    ("EspTroughOuter", 0.32, "ESP32"),  # 1.47mm pin center - 1.15mm half-width
    ("EspTroughW", 2.30, "ESP32"),      # Clears 2.0mm solder blobs
    ("EspTroughDepth", 2.20, "ESP32"),  # Clears 1.7mm pins + 2.0mm solder
    ("EspBtnNotchL", 12.0, "ESP32"),    # Clears EN/BOOT buttons at 3.4mm
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
oz_expr = "(Params.IntZ + Params.Floor)"
r_expr = "(Params.BossOD / 2)"

boss_positions = [
    ("SW", r_expr, r_expr),
    ("SE", f"{ox_expr} - {r_expr}", r_expr),
    ("NE", f"{ox_expr} - {r_expr}", f"{oy_expr} - {r_expr}"),
    ("NW", r_expr, f"{oy_expr} - {r_expr}"),
]

# -----------------------------------------------------------------------------
# 2. BASE BODY (PartDesign::Body)
# -----------------------------------------------------------------------------
base_body = doc.addObject("PartDesign::Body", "Base")
assembly.addObject(base_body)
base_xy = next(f for f in base_body.Origin.OriginFeatures if f.Role == "XY_Plane")

# Cross-box outer shell (leaves 3.2x3.2mm corner quadrants for concentric cylinders)
add_pd_feature(
    base_body, base_xy, "PartDesign::AdditiveBox", "OuterShell_X",
    {"x": r_expr, "y": "0", "z": "0"},
    {
        "Length": f"{ox_expr} - Params.BossOD",
        "Width": oy_expr,
        "Height": oz_expr,
    }
)

add_pd_feature(
    base_body, base_xy, "PartDesign::AdditiveBox", "OuterShell_Y",
    {"x": "0", "y": r_expr, "z": "0"},
    {
        "Length": ox_expr,
        "Width": f"{oy_expr} - Params.BossOD",
        "Height": oz_expr,
    }
)

# Inner Cavity
add_pd_feature(
    base_body, base_xy, "PartDesign::SubtractiveBox", "InnerCavity",
    {"x": "Params.Wall", "y": "Params.Wall", "z": "Params.Floor"},
    {
        "Length": "Params.IntX",
        "Width": "Params.IntY",
        "Height": "Params.IntZ + 1 mm",
    }
)

# 4x Concentric Corner Bosses / Rounded Exterior Corners & Pilot Holes
for tag, bx_expr, by_expr in boss_positions:
    add_pd_feature(
        base_body, base_xy, "PartDesign::AdditiveCylinder", f"Boss_{tag}",
        {"x": bx_expr, "y": by_expr, "z": "0"},
        {"Radius": r_expr, "Height": oz_expr}
    )
    add_pd_feature(
        base_body, base_xy, "PartDesign::SubtractiveCylinder", f"Pilot_{tag}",
        {"x": bx_expr, "y": by_expr, "z": f"{oz_expr} - Params.ScrewDepth"},
        {"Radius": "Params.PilotD / 2", "Height": "Params.ScrewDepth + 1 mm"}
    )

# -----------------------------------------------------------------------------
# 3. ESP32 RAILS (With Pin/Solder Troughs, Outer Capture Lips & Button Notches)
# -----------------------------------------------------------------------------
# Left rail outer edge starts at BossOD + 0.6mm = 7.0mm (zero boss collision)
esp_x0 = "(Params.BossOD + 0.6 mm + Params.EspLipW + Params.EspClear)"
esp_rx = f"({esp_x0} + Params.EspW)"
esp_y0 = "(Params.Wall + 0.2 mm)"

rail_total_w = "(Params.EspLipW + Params.EspClear + Params.EspInnerReach)"
rail_total_l = "(Params.EspL + Params.EspEndStopL)"
rail_total_h = "(Params.Floor + Params.EspShelfH + Params.EspThick)"
shelf_z = "(Params.Floor + Params.EspShelfH)"
trough_z = "(Params.Floor + Params.EspShelfH - Params.EspTroughDepth)"
trough_cut_h = "(Params.EspTroughDepth + Params.EspThick + 1 mm)"
notch_w = "(Params.EspInnerReach - Params.EspTroughOuter - Params.EspTroughW + 0.5 mm)"

# --- Left Rail ---
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

# --- Right Rail ---
add_pd_feature(
    base_body, base_xy, "PartDesign::AdditiveBox", "EspRailR_Block",
    {"x": f"{esp_rx} - Params.EspInnerReach", "y": esp_y0, "z": "0"},
    {"Length": rail_total_w, "Width": rail_total_l, "Height": rail_total_h}
)

add_pd_feature(
    base_body, base_xy, "PartDesign::SubtractiveBox", "EspRailR_ShelfCut",
    {
        "x": f"{esp_rx} - Params.EspInnerReach - 0.5 mm",
        "y": f"{esp_y0} - 0.1 mm",
        "z": shelf_z,
    },
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
    {
        "x": f"{esp_rx} - Params.EspInnerReach - 0.4 mm",
        "y": f"{esp_y0} - 0.1 mm",
        "z": trough_z,
    },
    {"Length": notch_w, "Width": "Params.EspBtnNotchL", "Height": trough_cut_h}
)

# USB-C Cutout (Centered on downward-facing USB-C port at Z = 5.4mm)
add_pd_feature(
    base_body, base_xy, "PartDesign::SubtractiveBox", "UsbCutout",
    {
        "x": f"{esp_x0} + (Params.EspW - Params.UsbW) / 2",
        "y": "-1 mm",
        "z": "Params.Floor",
    },
    {
        "Length": "Params.UsbW",
        "Width": "Params.Wall + 2 mm",
        "Height": "Params.UsbH",
    }
)

# -----------------------------------------------------------------------------
# 4. LD2410C CRADLE (3-Sided 1.7mm Lip + 4.25mm PCB Wing Supports)
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
    {
        "x": ld_ox0,
        "y": f"{ld_oy0} + Params.LdLipW",
        "z": "Params.Floor + Params.EspShelfH",
    },
    {
        "Length": "Params.LdL",
        "Width": "Params.LdW",
        "Height": "Params.LdLipH + 1 mm",
    }
)

add_pd_feature(
    base_body, base_xy, "PartDesign::SubtractiveBox", "LdSolderAndAntennaRelief",
    {
        "x": f"{ld_ox0} - 0.5 mm",
        "y": f"{ld_oy0} + Params.LdLipW + Params.LdWingW",
        "z": "Params.Floor",
    },
    {
        "Length": "Params.LdL - 1.5 mm + 0.5 mm",
        "Width": "Params.LdW - 2 * Params.LdWingW",
        "Height": "Params.EspShelfH + 1 mm",
    },
    refine=True
)

# -----------------------------------------------------------------------------
# 5. LID BODY (PartDesign::Body with Matching R=3.2mm Rounded Corners)
# -----------------------------------------------------------------------------
lid_body = doc.addObject("PartDesign::Body", "Lid")
assembly.addObject(lid_body)
lid_xy = next(f for f in lid_body.Origin.OriginFeatures if f.Role == "XY_Plane")

add_pd_feature(
    lid_body, lid_xy, "PartDesign::AdditiveBox", "LidPlate_X",
    {"x": r_expr, "y": "0", "z": "0"},
    {
        "Length": f"{ox_expr} - Params.BossOD",
        "Width": oy_expr,
        "Height": "Params.LidThick",
    }
)

add_pd_feature(
    lid_body, lid_xy, "PartDesign::AdditiveBox", "LidPlate_Y",
    {"x": "0", "y": r_expr, "z": "0"},
    {
        "Length": ox_expr,
        "Width": f"{oy_expr} - Params.BossOD",
        "Height": "Params.LidThick",
    }
)

for idx, (tag, bx_expr, by_expr) in enumerate(boss_positions):
    add_pd_feature(
        lid_body, lid_xy, "PartDesign::AdditiveCylinder", f"LidCorner_{tag}",
        {"x": bx_expr, "y": by_expr, "z": "0"},
        {"Radius": r_expr, "Height": "Params.LidThick"}
    )
    add_pd_feature(
        lid_body, lid_xy, "PartDesign::SubtractiveCylinder", f"Clearance_{tag}",
        {"x": bx_expr, "y": by_expr, "z": "-0.5 mm"},
        {"Radius": "Params.ClearanceD / 2", "Height": "Params.LidThick + 1 mm"}
    )
    add_pd_feature(
        lid_body, lid_xy, "PartDesign::SubtractiveCone", f"Countersink_{tag}",
        {
            "x": bx_expr,
            "y": by_expr,
            "z": "Params.LidThick - (Params.CsinkD - Params.ClearanceD) / (2 * tan(41 deg))",
        },
        {
            "Radius1": "Params.ClearanceD / 2",
            "Radius2": "Params.CsinkD / 2",
            "Height": "(Params.CsinkD - Params.ClearanceD) / (2 * tan(41 deg)) + 0.01 mm",
        },
        refine=(idx == len(boss_positions) - 1)
    )

lid_body.setExpression(".Placement.Base.x", f"{ox_expr} + 10 mm")

# -----------------------------------------------------------------------------
# 6. RECOMPUTE & EXPORT
# -----------------------------------------------------------------------------
doc.recompute()
Import.export([assembly], "esp32_ld2410_enclosure.step")