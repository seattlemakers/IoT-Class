import FreeCAD as App
import PartDesign
import Import

doc = App.newDocument("ESP32_LD2410_Clamshell")

# -----------------------------------------------------------------------------
# 1. NATIVE PARAMETER SET (App::VarSet)
# -----------------------------------------------------------------------------
params = doc.addObject("App::VarSet", "Params")

param_defs = [
    # Clamshell Enclosure Z-Stack
    ("Wall", 2.0, "Enclosure"),
    ("Floor", 2.0, "Enclosure"),
    ("LidRoof", 2.5, "Enclosure"),
    ("IntX", 63.0, "Enclosure"),
    ("IntY", 56.0, "Enclosure"),
    ("IntZ", 31.0, "Enclosure"),
    ("BaseWallH", 15.5, "Enclosure"),
    ("LipH", 2.0, "Enclosure"),
    ("LipClearXY", 0.15, "Enclosure"),
    ("LipClearZ", 0.20, "Enclosure"),
    ("LidOuterLipW", 0.95, "Enclosure"),
    # Concentric Corners & #4 x 5/8" Screw Bosses
    ("CornerR", 4.10, "Fasteners"),
    ("BaseBossR", 3.00, "Fasteners"),
    ("LidBossH", 8.0, "Fasteners"),
    ("BossGapZ", 0.20, "Fasteners"),
    ("PilotD", 2.4, "Fasteners"),
    ("ClearanceD", 3.2, "Fasteners"),
    ("CsinkD", 5.6, "Fasteners"),
    ("PilotDepth", 9.5, "Fasteners"),
    # ESP32-S (25.8 x 48.1 x 1.2 mm)
    ("EspW", 25.8, "ESP32"),
    ("EspL", 48.1, "ESP32"),
    ("EspThick", 1.2, "ESP32"),
    ("EspClear", 0.15, "ESP32"),
    ("EspShelfH", 5.0, "ESP32"),
    ("EspLipW", 1.5, "ESP32"),
    ("EspInnerReach", 3.65, "ESP32"),
    ("EspTroughOuter", 0.32, "ESP32"),
    ("EspTroughW", 2.30, "ESP32"),
    ("EspTroughDepth", 2.20, "ESP32"),
    ("EspBtnNotchL", 12.0, "ESP32"),
    ("UsbOvalW", 9.8, "ESP32"),         # 8.8mm port + 0.5mm gap per side
    ("UsbOvalH", 4.0, "ESP32"),         # 3.0mm port + 0.5mm gap per side
    ("UsbCenterZ", 3.5, "ESP32"),       # Relative to Floor (7.0mm shelf - 1.5mm = 5.5mm Z)
    # LD2410C (22.0 along Y x 16.0 along X x 1.7 mm Z)
    ("LdW", 22.3, "LD2410"),            # Y-axis span (22.0 + 0.3mm clearance)
    ("LdL", 16.3, "LD2410"),            # X-axis span (16.0 + 0.3mm clearance)
    ("LdThick", 1.7, "LD2410"),
    ("LdLipW", 1.5, "LD2410"),
    ("LdSideTrayW", 1.5, "LD2410"),     # 1.5mm narrow side shelves along -Y/+Y
    ("LdSideTrayL", 12.0, "LD2410"),    # 12.0mm length in +X past -X lip
    ("LdOutLedge", 0.50, "LD2410"),     # 0.5mm outboard ledge on -X header edge
    ("LdWallThick", 1.30, "LD2410"),    # Free-standing +X flex wall thickness
    # Snap-Hook, Groove & 45-Deg Ramp Parameters
    ("SnapOverhang", 0.50, "Snaps"),    # 0.5mm ridge/groove engagement
    ("SnapClearZ", 0.10, "Snaps"),      # Vertical clearance above PCB top surface
    ("SnapRidgeH", 1.20, "Snaps"),      # 0.6mm vertical shoulder + 0.6mm 45-deg ramp
    ("SnapRampH", 0.60, "Snaps"),       # 45-deg lead-in bevel height/width
]

for name, val, group in param_defs:
    params.addProperty("App::PropertyLength", name, group)
    setattr(params, name, val)


def add_pd_feature(body, plane, type_id, name, pos_exprs, prop_exprs, rot=None, refine=False):
    """Create a PartDesign feature attached to a Body origin plane with expressions."""
    feat = body.newObject(type_id, name)
    feat.AttachmentSupport = [(plane, "")]
    feat.MapMode = "FlatFace"
    if rot is not None:
        axis, angle = rot
        feat.AttachmentOffset = App.Placement(
            App.Vector(0, 0, 0),
            App.Rotation(App.Vector(*axis), angle)
        )
    for axis, expr in pos_exprs.items():
        feat.setExpression(f".AttachmentOffset.Base.{axis}", expr)
    for prop, expr in prop_exprs.items():
        feat.setExpression(prop, expr)
    if hasattr(feat, "Refine"):
        feat.Refine = refine
    return feat


def add_board_mounts_and_usb(body, xy_plane, xz_plane, prefix=""):
    """Add ESP32 rails/snaps, oval USB-C port, and LD2410 cradle/snaps to a Body."""
    shelf_z = "(Params.Floor + Params.EspShelfH)"
    trough_z = "(Params.Floor + Params.EspShelfH - Params.EspTroughDepth)"

    # -------------------------------------------------------------------------
    # A. ESP32 RAILS, FRONT HOLD-DOWN TABS (-Y) & REAR SNAP HOOKS (+Y)
    # -------------------------------------------------------------------------
    esp_x0 = "(Params.CornerR + Params.BaseBossR + 0.5 mm + Params.EspLipW + Params.EspClear)"
    esp_rx = f"({esp_x0} + Params.EspW)"
    esp_y0 = "(Params.Wall + 0.2 mm)"
    esp_ry = f"({esp_y0} + Params.EspL + 0.2 mm)"

    rail_total_w = "(Params.EspLipW + Params.EspClear + Params.EspInnerReach)"
    rail_total_h = "(Params.Floor + Params.EspShelfH + Params.EspThick)"
    trough_cut_h = "(Params.EspTroughDepth + Params.EspThick + 1 mm)"
    notch_w = "(Params.EspInnerReach - Params.EspTroughOuter - Params.EspTroughW + 0.5 mm)"
    esp_snap_top_z = "(Params.Floor + Params.EspShelfH + Params.EspThick + Params.SnapClearZ + Params.SnapRidgeH)"

    # Left Rail (-X)
    add_pd_feature(
        body, xy_plane, "PartDesign::AdditiveBox", f"{prefix}EspRailL_Block",
        {"x": f"{esp_x0} - Params.EspClear - Params.EspLipW", "y": esp_y0, "z": "0"},
        {"Length": rail_total_w, "Width": "Params.EspL + 0.2 mm", "Height": rail_total_h}
    )
    add_pd_feature(
        body, xy_plane, "PartDesign::SubtractiveBox", f"{prefix}EspRailL_ShelfCut",
        {"x": f"{esp_x0} - Params.EspClear", "y": f"{esp_y0} - 0.1 mm", "z": shelf_z},
        {
            "Length": "Params.EspClear + Params.EspInnerReach + 0.5 mm",
            "Width": "Params.EspL + 0.4 mm",
            "Height": "Params.EspThick + 1 mm",
        }
    )
    add_pd_feature(
        body, xy_plane, "PartDesign::SubtractiveBox", f"{prefix}EspRailL_Trough",
        {"x": f"{esp_x0} + Params.EspTroughOuter", "y": f"{esp_y0} - 0.1 mm", "z": trough_z},
        {"Length": "Params.EspTroughW", "Width": "Params.EspL + 0.4 mm", "Height": trough_cut_h}
    )
    add_pd_feature(
        body, xy_plane, "PartDesign::SubtractiveBox", f"{prefix}EspRailL_BtnNotch",
        {
            "x": f"{esp_x0} + Params.EspTroughOuter + Params.EspTroughW - 0.1 mm",
            "y": f"{esp_y0} - 0.1 mm",
            "z": trough_z,
        },
        {"Length": notch_w, "Width": "Params.EspBtnNotchL", "Height": trough_cut_h}
    )

    # Right Rail (+X)
    add_pd_feature(
        body, xy_plane, "PartDesign::AdditiveBox", f"{prefix}EspRailR_Block",
        {"x": f"{esp_rx} - Params.EspInnerReach", "y": esp_y0, "z": "0"},
        {"Length": rail_total_w, "Width": "Params.EspL + 0.2 mm", "Height": rail_total_h}
    )
    add_pd_feature(
        body, xy_plane, "PartDesign::SubtractiveBox", f"{prefix}EspRailR_ShelfCut",
        {"x": f"{esp_rx} - Params.EspInnerReach - 0.5 mm", "y": f"{esp_y0} - 0.1 mm", "z": shelf_z},
        {
            "Length": "Params.EspInnerReach + Params.EspClear + 0.5 mm",
            "Width": "Params.EspL + 0.4 mm",
            "Height": "Params.EspThick + 1 mm",
        }
    )
    add_pd_feature(
        body, xy_plane, "PartDesign::SubtractiveBox", f"{prefix}EspRailR_Trough",
        {
            "x": f"{esp_rx} - Params.EspTroughOuter - Params.EspTroughW",
            "y": f"{esp_y0} - 0.1 mm",
            "z": trough_z,
        },
        {"Length": "Params.EspTroughW", "Width": "Params.EspL + 0.4 mm", "Height": trough_cut_h}
    )
    add_pd_feature(
        body, xy_plane, "PartDesign::SubtractiveBox", f"{prefix}EspRailR_BtnNotch",
        {"x": f"{esp_rx} - Params.EspInnerReach - 0.4 mm", "y": f"{esp_y0} - 0.1 mm", "z": trough_z},
        {"Length": notch_w, "Width": "Params.EspBtnNotchL", "Height": trough_cut_h}
    )

    # ESP32 Front (-Y) Hold-Down Ridges (2x fixed tabs flanking USB-C shield pins)
    for side, tab_x in [("L", f"{esp_x0} + 3.5 mm"), ("R", f"{esp_rx} - 7.5 mm")]:
        add_pd_feature(
            body, xy_plane, "PartDesign::AdditiveBox", f"{prefix}EspFrontTab_{side}",
            {"x": tab_x, "y": "Params.Wall", "z": "0"},
            {"Length": "4.0 mm", "Width": "0.2 mm + Params.SnapOverhang", "Height": esp_snap_top_z}
        )
        add_pd_feature(
            body, xy_plane, "PartDesign::SubtractiveBox", f"{prefix}EspFrontSlot_{side}",
            {"x": f"({tab_x}) - 0.1 mm", "y": esp_y0, "z": "Params.Floor"},
            {
                "Length": "4.2 mm",
                "Width": "Params.SnapOverhang + 0.2 mm",
                "Height": "Params.EspShelfH + Params.EspThick + Params.SnapClearZ",
            }
        )

    # ESP32 Rear (+Y) Cantilever Snap Hooks + 45-Deg Lead-In Ramps
    for side, post_x in [("L", f"{esp_x0} + 4.0 mm"), ("R", f"{esp_rx} - 8.0 mm")]:
        add_pd_feature(
            body, xy_plane, "PartDesign::AdditiveBox", f"{prefix}EspRearSnap_{side}",
            {"x": post_x, "y": f"{esp_ry} - Params.SnapOverhang", "z": "0"},
            {"Length": "4.0 mm", "Width": "Params.SnapOverhang + 1.4 mm", "Height": esp_snap_top_z}
        )
        add_pd_feature(
            body, xy_plane, "PartDesign::SubtractiveBox", f"{prefix}EspRearUndercut_{side}",
            {"x": f"({post_x}) - 0.1 mm", "y": f"{esp_ry} - Params.SnapOverhang - 0.1 mm", "z": "Params.Floor"},
            {
                "Length": "4.2 mm",
                "Width": "Params.SnapOverhang + 0.1 mm",
                "Height": "Params.EspShelfH + Params.EspThick + Params.SnapClearZ",
            }
        )
        # 45-deg ramp on top -Y edge (rot +45 deg about X)
        add_pd_feature(
            body, xy_plane, "PartDesign::SubtractiveBox", f"{prefix}EspRearRamp_{side}",
            {
                "x": f"({post_x}) - 0.1 mm",
                "y": f"{esp_ry} - Params.SnapOverhang",
                "z": f"{esp_snap_top_z} - Params.SnapRampH",
            },
            {"Length": "4.2 mm", "Width": "2.0 mm", "Height": "2.0 mm"},
            rot=((1, 0, 0), 45.0)
        )

    # USB-C Stadium Oval Cutout (Y = 0 wall)
    usb_cx = f"({esp_x0} + Params.EspW / 2)"
    usb_cz = "(Params.Floor + Params.UsbCenterZ)"
    usb_half_flat = "((Params.UsbOvalW - Params.UsbOvalH) / 2)"

    add_pd_feature(
        body, xy_plane, "PartDesign::SubtractiveBox", f"{prefix}UsbOval_Center",
        {
            "x": f"{usb_cx} - {usb_half_flat}",
            "y": "-1 mm",
            "z": f"{usb_cz} - Params.UsbOvalH / 2",
        },
        {
            "Length": "Params.UsbOvalW - Params.UsbOvalH",
            "Width": "Params.Wall + 2 mm",
            "Height": "Params.UsbOvalH",
        }
    )
    for side, sign in [("L", "-"), ("R", "+")]:
        add_pd_feature(
            body, xz_plane, "PartDesign::SubtractiveCylinder", f"{prefix}UsbOval_End{side}",
            {
                "x": f"{usb_cx} {sign} {usb_half_flat}",
                "y": usb_cz,
                "z": "-(Params.Wall + 1 mm)",
            },
            {"Radius": "Params.UsbOvalH / 2", "Height": "Params.Wall + 2 mm"}
        )

    # -------------------------------------------------------------------------
    # B. LD2410C HOLDER (-X Header Rail, 12mm Side Trays, +X Flex Wall & Ramps)
    # -------------------------------------------------------------------------
    ld_x0 = "43.5 mm"  # Inner (+X) face of the -X header lip
    ld_y0 = "(Params.Wall + (Params.IntY - Params.LdW) / 2)"
    ld_top_z = "(Params.Floor + Params.EspShelfH + Params.LdThick)"
    ld_snap_top_z = f"({ld_top_z} + Params.SnapClearZ + Params.SnapRidgeH)"
    ld_hdr_reach = "(Params.LdOutLedge + Params.EspTroughW + 1.05 mm)"

    # 1. -X Header Rail
    add_pd_feature(
        body, xy_plane, "PartDesign::AdditiveBox", f"{prefix}LdHeaderRail_Block",
        {"x": f"{ld_x0} - Params.LdLipW", "y": f"{ld_y0} - Params.LdLipW", "z": "0"},
        {
            "Length": f"Params.LdLipW + {ld_hdr_reach}",
            "Width": "Params.LdW + 2 * Params.LdLipW",
            "Height": ld_top_z,
        }
    )
    add_pd_feature(
        body, xy_plane, "PartDesign::SubtractiveBox", f"{prefix}LdHeaderRail_ShelfCut",
        {"x": ld_x0, "y": ld_y0, "z": shelf_z},
        {
            "Length": f"{ld_hdr_reach} + 0.5 mm",
            "Width": "Params.LdW",
            "Height": "Params.LdThick + 1 mm",
        }
    )
    add_pd_feature(
        body, xy_plane, "PartDesign::SubtractiveBox", f"{prefix}LdHeaderRail_Trough",
        {"x": f"{ld_x0} + Params.LdOutLedge", "y": f"{ld_y0} + Params.LdSideTrayW", "z": trough_z},
        {
            "Length": "Params.EspTroughW",
            "Width": "Params.LdW - 2 * Params.LdSideTrayW",
            "Height": "Params.EspTroughDepth + Params.LdThick + 1 mm",
        }
    )

    # 2. Short Side-Trays along -Y and +Y (1.5mm shelf width, 12.0mm length in +X)
    add_pd_feature(
        body, xy_plane, "PartDesign::AdditiveBox", f"{prefix}LdSideTray_MinY",
        {"x": ld_x0, "y": f"{ld_y0} - Params.LdLipW", "z": "0"},
        {
            "Length": "Params.LdSideTrayL",
            "Width": "Params.LdLipW + Params.LdSideTrayW",
            "Height": ld_top_z,
        }
    )
    add_pd_feature(
        body, xy_plane, "PartDesign::SubtractiveBox", f"{prefix}LdSideTray_MinY_Shelf",
        {"x": f"{ld_x0} - 0.1 mm", "y": ld_y0, "z": shelf_z},
        {
            "Length": "Params.LdSideTrayL + 0.2 mm",
            "Width": "Params.LdSideTrayW + 0.2 mm",
            "Height": "Params.LdThick + 1 mm",
        }
    )

    add_pd_feature(
        body, xy_plane, "PartDesign::AdditiveBox", f"{prefix}LdSideTray_MaxY",
        {"x": ld_x0, "y": f"{ld_y0} + Params.LdW - Params.LdSideTrayW", "z": "0"},
        {
            "Length": "Params.LdSideTrayL",
            "Width": "Params.LdSideTrayW + Params.LdLipW",
            "Height": ld_top_z,
        }
    )
    add_pd_feature(
        body, xy_plane, "PartDesign::SubtractiveBox", f"{prefix}LdSideTray_MaxY_Shelf",
        {"x": f"{ld_x0} - 0.1 mm", "y": f"{ld_y0} + Params.LdW - Params.LdSideTrayW - 0.2 mm", "z": shelf_z},
        {
            "Length": "Params.LdSideTrayL + 0.2 mm",
            "Width": "Params.LdSideTrayW + 0.2 mm",
            "Height": "Params.LdThick + 1 mm",
        }
    )

    # 3. Two Snap Hooks on -X Header Lip + 45-Deg Lead-In Ramps
    for side, hook_y in [("MinY", f"{ld_y0} + 0.4 mm"), ("MaxY", f"{ld_y0} + Params.LdW - 3.9 mm")]:
        add_pd_feature(
            body, xy_plane, "PartDesign::AdditiveBox", f"{prefix}LdSnapHook_{side}",
            {"x": f"{ld_x0} - Params.LdLipW", "y": hook_y, "z": "0"},
            {
                "Length": "Params.LdLipW + Params.SnapOverhang",
                "Width": "3.5 mm",
                "Height": ld_snap_top_z,
            }
        )
        add_pd_feature(
            body, xy_plane, "PartDesign::SubtractiveBox", f"{prefix}LdSnapUndercut_{side}",
            {"x": ld_x0, "y": f"({hook_y}) - 0.1 mm", "z": shelf_z},
            {
                "Length": "Params.SnapOverhang + 0.2 mm",
                "Width": "3.7 mm",
                "Height": "Params.LdThick + Params.SnapClearZ",
            }
        )
        # 45-deg ramp on top +X edge (rot -45 deg about Y)
        add_pd_feature(
            body, xy_plane, "PartDesign::SubtractiveBox", f"{prefix}LdSnapRamp_{side}",
            {
                "x": f"{ld_x0} + Params.SnapOverhang",
                "y": f"({hook_y}) - 0.1 mm",
                "z": f"{ld_snap_top_z} - Params.SnapRampH",
            },
            {"Length": "2.0 mm", "Width": "3.7 mm", "Height": "2.0 mm"},
            rot=((0, 1, 0), -45.0)
        )

    # 4. Free-Standing Flex Wall on +X Edge + Groove + 45-Deg Lead-In Ramp
    ld_wall_x0 = f"({ld_x0} + Params.LdL - Params.SnapOverhang)"
    ld_wall_y0 = f"({ld_y0} + 2.0 mm)"
    ld_wall_w = "(Params.LdW - 4.0 mm)"

    add_pd_feature(
        body, xy_plane, "PartDesign::AdditiveBox", f"{prefix}LdFlexWall_Block",
        {"x": ld_wall_x0, "y": ld_wall_y0, "z": "0"},
        {
            "Length": "Params.SnapOverhang + Params.LdWallThick",
            "Width": ld_wall_w,
            "Height": ld_snap_top_z,
        }
    )
    add_pd_feature(
        body, xy_plane, "PartDesign::SubtractiveBox", f"{prefix}LdFlexWall_Groove",
        {"x": f"{ld_wall_x0} - 0.1 mm", "y": f"{ld_wall_y0} - 0.1 mm", "z": shelf_z},
        {
            "Length": "Params.SnapOverhang + 0.1 mm",
            "Width": f"{ld_wall_w} + 0.2 mm",
            "Height": "Params.LdThick + Params.SnapClearZ",
        }
    )
    # 45-deg ramp on top -X edge of flex wall (rot -45 deg about Y)
    add_pd_feature(
        body, xy_plane, "PartDesign::SubtractiveBox", f"{prefix}LdFlexWall_Ramp",
        {
            "x": ld_wall_x0,
            "y": f"{ld_wall_y0} - 0.1 mm",
            "z": f"{ld_snap_top_z} - Params.SnapRampH",
        },
        {"Length": "2.0 mm", "Width": f"{ld_wall_w} + 0.2 mm", "Height": "2.0 mm"},
        rot=((0, 1, 0), -45.0),
        refine=True
    )


assembly = doc.addObject("App::Part", "EnclosureAssembly")

ox_expr = "(Params.IntX + 2 * Params.Wall)"
oy_expr = "(Params.IntY + 2 * Params.Wall)"
cr_expr = "Params.CornerR"
lip_inset = "(Params.LidOuterLipW + Params.LipClearXY)"
base_split_z = "(Params.Floor + Params.BaseWallH)"
base_lip_top_z = f"({base_split_z} + Params.LipH)"
base_boss_top_z = "(Params.Floor + Params.IntZ + Params.LidRoof - Params.LidBossH - Params.BossGapZ)"

boss_positions = [
    ("MinX_MinY", cr_expr, cr_expr),
    ("MaxX_MinY", f"{ox_expr} - {cr_expr}", cr_expr),
    ("MaxX_MaxY", f"{ox_expr} - {cr_expr}", f"{oy_expr} - {cr_expr}"),
    ("MinX_MaxY", cr_expr, f"{oy_expr} - {cr_expr}"),
]

# -----------------------------------------------------------------------------
# 2. FULL CLAMSHELL BASE BODY
# -----------------------------------------------------------------------------
base_body = doc.addObject("PartDesign::Body", "Base")
assembly.addObject(base_body)
base_xy = next(f for f in base_body.Origin.OriginFeatures if f.Role == "XY_Plane")
base_xz = next(f for f in base_body.Origin.OriginFeatures if f.Role == "XZ_Plane")

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

add_pd_feature(
    base_body, base_xy, "PartDesign::SubtractiveBox", "InnerCavity",
    {"x": "Params.Wall", "y": "Params.Wall", "z": "Params.Floor"},
    {"Length": "Params.IntX", "Width": "Params.IntY", "Height": "Params.IntZ + 1 mm"}
)

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

add_board_mounts_and_usb(base_body, base_xy, base_xz, prefix="Base_")

# -----------------------------------------------------------------------------
# 3. CLAMSHELL LID BODY
# -----------------------------------------------------------------------------
lid_body = doc.addObject("PartDesign::Body", "Lid")
assembly.addObject(lid_body)
lid_xy = next(f for f in lid_body.Origin.OriginFeatures if f.Role == "XY_Plane")

lid_h_expr = "(Params.LidRoof + Params.IntZ - Params.BaseWallH)"
lid_rabbet_z = f"({lid_h_expr} - Params.LipH - Params.LipClearZ)"
lid_socket_r = "(Params.CornerR - Params.LidOuterLipW)"

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

add_pd_feature(
    lid_body, lid_xy, "PartDesign::SubtractiveBox", "LidCavity",
    {"x": "Params.Wall", "y": "Params.Wall", "z": "Params.LidRoof"},
    {"Length": "Params.IntX", "Width": "Params.IntY", "Height": lid_h_expr}
)

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

for idx, (tag, bx_expr, by_expr) in enumerate(boss_positions):
    add_pd_feature(
        lid_body, lid_xy, "PartDesign::AdditiveCylinder", f"LidBoss_{tag}",
        {"x": bx_expr, "y": by_expr, "z": "0"},
        {"Radius": lid_socket_r, "Height": "Params.LidBossH"}
    )
    add_pd_feature(
        lid_body, lid_xy, "PartDesign::SubtractiveCylinder", f"LidBossSocket_{tag}",
        {"x": bx_expr, "y": by_expr, "z": "Params.LidBossH"},
        {"Radius": lid_socket_r, "Height": lid_h_expr}
    )
    add_pd_feature(
        lid_body, lid_xy, "PartDesign::SubtractiveCylinder", f"Clearance_{tag}",
        {"x": bx_expr, "y": by_expr, "z": "-0.5 mm"},
        {"Radius": "Params.ClearanceD / 2", "Height": "Params.LidBossH + 1 mm"}
    )
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

lid_body.setExpression(".Placement.Base.x", f"{ox_expr} + 10 mm")

# -----------------------------------------------------------------------------
# 4. FAST-ITERATION TEST PLATE BODY (Floor + USB Wall Tab + Mounts Only)
# -----------------------------------------------------------------------------
test_body = doc.addObject("PartDesign::Body", "TestPlate")
test_xy = next(f for f in test_body.Origin.OriginFeatures if f.Role == "XY_Plane")
test_xz = next(f for f in test_body.Origin.OriginFeatures if f.Role == "XZ_Plane")

add_pd_feature(
    test_body, test_xy, "PartDesign::AdditiveBox", "TestFloor",
    {"x": "6.0 mm", "y": "0", "z": "0"},
    {"Length": "56.5 mm", "Width": "54.5 mm", "Height": "Params.Floor"}
)

add_pd_feature(
    test_body, test_xy, "PartDesign::AdditiveBox", "TestUsbWallStub",
    {"x": "7.5 mm", "y": "0", "z": "0"},
    {
        "Length": "Params.EspW + 2 * Params.EspLipW + 0.4 mm",
        "Width": "Params.Wall",
        "Height": "Params.Floor + Params.EspShelfH + Params.EspThick + 2.5 mm",
    }
)

add_board_mounts_and_usb(test_body, test_xy, test_xz, prefix="Test_")
test_body.setExpression(".Placement.Base.y", f"-({oy_expr} + 10 mm)")

# -----------------------------------------------------------------------------
# 5. RECOMPUTE & EXPORT BOTH STEP FILES
# -----------------------------------------------------------------------------
doc.recompute()
Import.export([assembly], "esp32_ld2410_clamshell.step")
Import.export([test_body], "esp32_ld2410_testplate.step")