import os
import FreeCAD as App
import PartDesign
import Draft
import Import

doc = App.newDocument("ESP_Sensor_Clamshell")

# =============================================================================
# 0. BOARD & MODULE PRESET SELECTORS
# =============================================================================
ESP_TYPE = "NodeMCU-ESP32"   # Options: "NodeMCU-ESP32", "NodeMCU-ESP8266"
MOD_TYPE = "LD2410C"         # Options: "LD2410C"

ESP_PRESETS = {
    "NodeMCU-ESP32": {
        "EspW": 25.8,
        "EspL": 48.1,
        "EspThick": 1.2,
        "EspRearClearY": 0.40,
        "UsbOvalW": 9.8,
        "UsbOvalH": 4.0,
        "UsbCenterZ": 3.5,
        "Label": "NodeMCU-ESP32",
    },
    "NodeMCU-ESP8266": {
        "EspW": 25.8,
        "EspL": 48.1,
        "EspThick": 1.6,
        "EspRearClearY": -0.20,
        "UsbOvalW": 9.8,
        "UsbOvalH": 4.0,
        "UsbCenterZ": 3.5,
        "Label": "NodeMCU-ESP8266",
    },
}

MOD_PRESETS = {
    "LD2410C": {
        "LdW": 22.3,
        "LdL": 16.3,
        "LdThick": 1.7,
        "LdLipW": 1.5,
        "LdSideTrayW": 1.5,
        "LdSideTrayL": 12.0,
        "LdOutLedge": 0.50,
        "LdWallThick": 1.30,
        "Label": "LD2410C",
    },
}

esp_cfg = ESP_PRESETS[ESP_TYPE]
mod_cfg = MOD_PRESETS[MOD_TYPE]

# =============================================================================
# 1. NATIVE PARAMETER SET (App::VarSet)
# =============================================================================
params = doc.addObject("App::VarSet", "Params")

param_defs = [
    # --- Primary Module: ESP Board ---
    ("EspW", esp_cfg["EspW"], "1_ESP", "PCB width (X)"),
    ("EspL", esp_cfg["EspL"], "1_ESP", "PCB length (Y)"),
    ("EspThick", esp_cfg["EspThick"], "1_ESP", "PCB thickness (Z)"),
    ("EspClear", 0.15, "1_ESP", "Radial clearance around PCB in X"),
    ("EspRearClearY", esp_cfg["EspRearClearY"], "1_ESP", "Lengthwise Y clearance to rigid rail stop"),
    ("EspEndStopL", 1.50, "1_ESP", "Rigid +Y end-stop wall thickness on rails"),
    ("EspFrontGroove", 0.20, "1_ESP", "Groove depth in -Y wall for lengthwise relief"),
    ("EspShelfH", 5.0, "1_ESP", "Height of PCB support shelf above floor"),
    ("EspLipW", 1.5, "1_ESP", "Width of outer PCB capture lip"),
    ("EspInnerReach", 3.65, "1_ESP", "Total inward reach of rail from PCB edge"),
    ("EspTroughOuter", 0.32, "1_ESP", "Outboard flat ledge width before pin trough"),
    ("EspTroughW", 2.30, "1_ESP", "Width of solder/pin trough"),
    ("EspTroughDepth", 2.20, "1_ESP", "Depth of solder/pin trough below shelf"),
    ("EspBtnNotchL", 12.0, "1_ESP", "Length of inner rail notch for EN/BOOT buttons"),
    ("UsbOvalW", esp_cfg["UsbOvalW"], "1_ESP", "USB oval width (port width + clearance)"),
    ("UsbOvalH", esp_cfg["UsbOvalH"], "1_ESP", "USB oval height (port height + clearance)"),
    ("UsbCenterZ", esp_cfg["UsbCenterZ"], "1_ESP", "USB center Z relative to floor"),

    # --- Secondary Module: Sensor Board ---
    ("LdW", mod_cfg["LdW"], "2_SecondaryModule", "Module Y span (PCB length + 0.3mm clearance)"),
    ("LdL", mod_cfg["LdL"], "2_SecondaryModule", "Module X span (PCB width + 0.3mm clearance)"),
    ("LdThick", mod_cfg["LdThick"], "2_SecondaryModule", "Module PCB thickness (Z)"),
    ("LdLipW", mod_cfg["LdLipW"], "2_SecondaryModule", "Outer capture lip width"),
    ("LdSideTrayW", mod_cfg["LdSideTrayW"], "2_SecondaryModule", "Width of -Y/+Y side support shelves"),
    ("LdSideTrayL", mod_cfg["LdSideTrayL"], "2_SecondaryModule", "Length of side shelves along +X"),
    ("LdOutLedge", mod_cfg["LdOutLedge"], "2_SecondaryModule", "Outboard ledge width on -X header edge"),
    ("LdWallThick", mod_cfg["LdWallThick"], "2_SecondaryModule", "Thickness of +X free-standing flex wall"),

    # --- Snap Hooks, Ramps, Base Fillet & Floor Labels ---
    ("SnapWidth", 5.00, "3_Snaps", "Width (X) of each ESP rear snap clip"),
    ("SnapStemThick", 1.00, "3_Snaps", "Thickness (Y) of ESP rear snap stem (2 perimeters)"),
    ("SnapOverhang", 0.50, "3_Snaps", "Nominal snap hook / groove overhang depth"),
    ("SnapStemSetback", 0.10, "3_Snaps", "Y setback of clip stem behind rigid rail stop"),
    ("SnapClearZ", 0.10, "3_Snaps", "Vertical clearance between PCB top and hook"),
    ("SnapRidgeH", 1.20, "3_Snaps", "Total height of snap hook above PCB top"),
    ("SnapRampH", 0.60, "3_Snaps", "Height of 45-deg lead-in ramp"),
    ("SnapFilletR", 1.00, "3_Snaps", "Base fillet radius at root of snap clips"),
    ("LabelDepth", 0.45, "3_Snaps", "Recessed floor text depth (3 layers at 0.15mm)"),

    # --- Fasteners (#4 x 5/8" Flat-Head Wood Screws, +1.0mm Thread Engagement) ---
    ("CornerR", 4.10, "4_Fasteners", "Exterior corner radius & boss center offset"),
    ("BaseBossR", 3.00, "4_Fasteners", "Base boss radius (6.0mm OD)"),
    ("LidBossH", 7.0, "4_Fasteners", "Upper boss height in Lid (7.0mm = +1.0mm thread bite)"),
    ("BossGapZ", 0.20, "4_Fasteners", "Axial gap between bosses to clamp perimeter seam"),
    ("PilotD", 2.4, "4_Fasteners", "Pilot hole diameter for #4 wood screw"),
    ("ClearanceD", 3.2, "4_Fasteners", "Lid through-hole clearance diameter"),
    ("CsinkD", 5.6, "4_Fasteners", "82-deg flat-head countersink outer diameter"),
    ("PilotDepth", 10.5, "4_Fasteners", "Pilot hole depth in Base boss"),

    # --- Enclosure Margins & Z-Split (Locked IntZ = 31.0mm for Lid Interchangeability) ---
    ("Wall", 2.0, "5_Enclosure", "Outer wall thickness"),
    ("Floor", 2.0, "5_Enclosure", "Base floor thickness"),
    ("LidRoof", 2.5, "5_Enclosure", "Lid roof thickness"),
    ("ModuleGapX", 5.8, "5_Enclosure", "X gap between ESP rail and Secondary cradle"),
    ("RightMarginX", 3.9, "5_Enclosure", "Clearance between +X flex wall and +X inner wall"),
    ("RearMarginY", 7.9, "5_Enclosure", "Internal Y clearance beyond ESP length"),
    ("BaseWallH", 15.5, "5_Enclosure", "Base outer wall height above floor to split line"),
    ("LipH", 2.0, "5_Enclosure", "Height of perimeter nesting rabbet tongue"),
    ("LipClearXY", 0.15, "5_Enclosure", "Radial clearance on nesting rabbet joint"),
    ("LipClearZ", 0.20, "5_Enclosure", "Axial clearance on nesting rabbet joint"),
    ("LidOuterLipW", 0.95, "5_Enclosure", "Outer skirt thickness on Lid rabbet"),
    ("IntX", 63.0, "5_Enclosure", "Auto-computed internal X span"),
    ("IntY", 56.0, "5_Enclosure", "Auto-computed internal Y span"),
    ("IntZ", 31.0, "5_Enclosure", "Internal Z height (fixed so all Bases share one Lid)"),
]

for name, val, group, doc_str in param_defs:
    # App::PropertyDistance allows negative offsets (such as EspRearClearY = -0.20)
    params.addProperty("App::PropertyDistance", name, group, doc_str)
    setattr(params, name, val)

params.setExpression(
    "IntX",
    "CornerR + BaseBossR + 0.5 mm + 2 * (EspLipW + EspClear) + EspW "
    "+ ModuleGapX + LdLipW + LdL + LdWallThick + RightMarginX - 2 * Wall"
)
params.setExpression(
    "IntY",
    "EspL + RearMarginY > LdW + 2 * LdLipW + 6 mm "
    "? EspL + RearMarginY : LdW + 2 * LdLipW + 6 mm"
)


def find_system_font():
    """Return a valid TrueType font path on Debian/Linux, macOS, or Windows."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def add_recessed_floor_label(body, name, text, center_x, center_y, font_size):
    """Engrave a 90-deg Y-oriented label into the top of the Floor (Z = Floor)."""
    font_path = find_system_font()
    if not font_path or not text:
        return

    floor_z = float(params.Floor)
    ss = Draft.make_shapestring(String=text, FontFile=font_path, Size=font_size, Tracking=0.0)
    ss.Label = f"{name}_ShapeString"
    ss.Placement = App.Placement(
        App.Vector(0, 0, floor_z),
        App.Rotation(App.Vector(0, 0, 1), 90.0)
    )
    if hasattr(ss, "ViewObject") and ss.ViewObject:
        ss.ViewObject.Visibility = False

    doc.recompute()
    bb = ss.Shape.BoundBox
    ss.Placement.Base = App.Vector(
        center_x - bb.Center.x,
        center_y - bb.Center.y,
        floor_z
    )

    body.addObject(ss)
    pocket = body.newObject("PartDesign::Pocket", name)
    pocket.Profile = (ss, [""])
    pocket.setExpression("Length", "Params.LabelDepth")
    pocket.Refine = True


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
    """Add ESP rails with rigid +Y end-stops, 5.0x1.0mm clips, secondary cradle, fillets, and labels."""
    shelf_z = "(Params.Floor + Params.EspShelfH)"
    trough_z = "(Params.Floor + Params.EspShelfH - Params.EspTroughDepth)"

    # -------------------------------------------------------------------------
    # A. ESP RAILS (With Rigid +Y End-Stops), -Y GROOVE & 5.0x1.0mm +Y CLIPS
    # -------------------------------------------------------------------------
    esp_x0 = "(Params.CornerR + Params.BaseBossR + 0.5 mm + Params.EspLipW + Params.EspClear)"
    esp_rx = f"({esp_x0} + Params.EspW)"
    esp_y0 = "(Params.Wall + 0.2 mm)"
    esp_ry = f"({esp_y0} + Params.EspL + Params.EspRearClearY)"

    rail_total_w = "(Params.EspLipW + Params.EspClear + Params.EspInnerReach)"
    rail_total_l = "(Params.EspL + Params.EspRearClearY + Params.EspEndStopL)"
    rail_cut_l = "(Params.EspL + Params.EspRearClearY + 0.1 mm)"
    rail_total_h = "(Params.Floor + Params.EspShelfH + Params.EspThick)"
    trough_cut_h = "(Params.EspTroughDepth + Params.EspThick + 1 mm)"
    notch_w = "(Params.EspInnerReach - Params.EspTroughOuter - Params.EspTroughW + 0.5 mm)"
    esp_snap_top_z = "(Params.Floor + Params.EspShelfH + Params.EspThick + Params.SnapClearZ + Params.SnapRidgeH)"

    # Left Rail (-X)
    add_pd_feature(
        body, xy_plane, "PartDesign::AdditiveBox", f"{prefix}EspRailL_Block",
        {"x": f"{esp_x0} - Params.EspClear - Params.EspLipW", "y": esp_y0, "z": "0"},
        {"Length": rail_total_w, "Width": rail_total_l, "Height": rail_total_h}
    )
    add_pd_feature(
        body, xy_plane, "PartDesign::SubtractiveBox", f"{prefix}EspRailL_ShelfCut",
        {"x": f"{esp_x0} - Params.EspClear", "y": f"{esp_y0} - 0.1 mm", "z": shelf_z},
        {
            "Length": "Params.EspClear + Params.EspInnerReach + 0.5 mm",
            "Width": rail_cut_l,
            "Height": "Params.EspThick + 1 mm",
        }
    )
    add_pd_feature(
        body, xy_plane, "PartDesign::SubtractiveBox", f"{prefix}EspRailL_Trough",
        {"x": f"{esp_x0} + Params.EspTroughOuter", "y": f"{esp_y0} - 0.1 mm", "z": trough_z},
        {"Length": "Params.EspTroughW", "Width": rail_cut_l, "Height": trough_cut_h}
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
        {"Length": rail_total_w, "Width": rail_total_l, "Height": rail_total_h}
    )
    add_pd_feature(
        body, xy_plane, "PartDesign::SubtractiveBox", f"{prefix}EspRailR_ShelfCut",
        {"x": f"{esp_rx} - Params.EspInnerReach - 0.5 mm", "y": f"{esp_y0} - 0.1 mm", "z": shelf_z},
        {
            "Length": "Params.EspInnerReach + Params.EspClear + 0.5 mm",
            "Width": rail_cut_l,
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
        {"Length": "Params.EspTroughW", "Width": rail_cut_l, "Height": trough_cut_h}
    )
    add_pd_feature(
        body, xy_plane, "PartDesign::SubtractiveBox", f"{prefix}EspRailR_BtnNotch",
        {"x": f"{esp_rx} - Params.EspInnerReach - 0.4 mm", "y": f"{esp_y0} - 0.1 mm", "z": trough_z},
        {"Length": notch_w, "Width": "Params.EspBtnNotchL", "Height": trough_cut_h}
    )

    # ESP Front (-Y) Hold-Down Ridges + 0.20mm Relief Groove in -Y Wall
    for side, tab_x in [("L", f"{esp_x0} + 3.5 mm"), ("R", f"{esp_rx} - 7.5 mm")]:
        add_pd_feature(
            body, xy_plane, "PartDesign::AdditiveBox", f"{prefix}EspFrontTab_{side}",
            {"x": tab_x, "y": "Params.Wall", "z": "0"},
            {"Length": "4.0 mm", "Width": "0.2 mm + Params.SnapOverhang", "Height": esp_snap_top_z}
        )
        add_pd_feature(
            body, xy_plane, "PartDesign::SubtractiveBox", f"{prefix}EspFrontSlot_{side}",
            {"x": f"({tab_x}) - 0.1 mm", "y": f"{esp_y0} - Params.EspFrontGroove", "z": "Params.Floor"},
            {
                "Length": "4.2 mm",
                "Width": "Params.EspFrontGroove + Params.SnapOverhang + 0.3 mm",
                "Height": "Params.EspShelfH + Params.EspThick + Params.SnapClearZ",
            }
        )

    add_pd_feature(
        body, xy_plane, "PartDesign::SubtractiveBox", f"{prefix}EspFrontWallGroove",
        {
            "x": f"{esp_x0} - Params.EspClear",
            "y": "Params.Wall - Params.EspFrontGroove",
            "z": shelf_z,
        },
        {
            "Length": "Params.EspW + 2 * Params.EspClear",
            "Width": "Params.EspFrontGroove + 0.25 mm",
            "Height": "Params.EspThick + Params.SnapClearZ",
        }
    )

    # ESP Rear (+Y) Cantilever Snap Hooks (5.0mm wide x 1.0mm thick stem, 1.0mm base fillet)
    hook_tip_y = f"({esp_ry} - Params.SnapOverhang - 0.10 mm)"
    hook_reach_y = "(Params.SnapOverhang + 0.10 mm + Params.SnapStemSetback)"

    for side, post_x in [
        ("L", f"{esp_x0} + 4.0 mm"),
        ("R", f"{esp_rx} - 4.0 mm - Params.SnapWidth"),
    ]:
        add_pd_feature(
            body, xy_plane, "PartDesign::AdditiveBox", f"{prefix}EspRearSnap_{side}",
            {"x": post_x, "y": hook_tip_y, "z": "0"},
            {
                "Length": "Params.SnapWidth",
                "Width": f"{hook_reach_y} + Params.SnapStemThick",
                "Height": esp_snap_top_z,
            }
        )
        add_pd_feature(
            body, xy_plane, "PartDesign::SubtractiveBox", f"{prefix}EspRearUndercut_{side}",
            {"x": f"({post_x}) - 0.1 mm", "y": f"{hook_tip_y} - 0.1 mm", "z": "Params.Floor"},
            {
                "Length": "Params.SnapWidth + 0.2 mm",
                "Width": f"{hook_reach_y} + 0.1 mm",
                "Height": "Params.EspShelfH + Params.EspThick + Params.SnapClearZ",
            }
        )
        add_pd_feature(
            body, xy_plane, "PartDesign::SubtractiveBox", f"{prefix}EspRearRamp_{side}",
            {
                "x": f"({post_x}) - 0.1 mm",
                "y": hook_tip_y,
                "z": f"{esp_snap_top_z} - Params.SnapRampH",
            },
            {"Length": "Params.SnapWidth + 0.2 mm", "Width": "2.0 mm", "Height": "2.0 mm"},
            rot=((1, 0, 0), 45.0)
        )

    # USB Stadium Oval Cutout (Y = 0 wall)
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
    # B. SECONDARY MODULE CRADLE
    # -------------------------------------------------------------------------
    ld_x0 = f"({esp_rx} + Params.EspClear + Params.EspLipW + Params.ModuleGapX + Params.LdLipW)"
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

    # 2. Short Side-Trays along -Y and +Y
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

    # 4. Free-Standing Flex Wall on +X Edge + Groove + 45-Deg Ramp
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
    last_feat = add_pd_feature(
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

    # -------------------------------------------------------------------------
    # C. NATIVE BASE FILLET (Applied Before Floor Text Pockets)
    # -------------------------------------------------------------------------
    doc.recompute()

    floor_z = float(params.Floor)
    snap_w_val = float(params.SnapWidth)
    stem_t_val = float(params.SnapStemThick)
    stem_y_min = (
        float(params.Wall) + 0.2 + float(params.EspL)
        + float(params.EspRearClearY) + float(params.SnapStemSetback)
    )
    esp_x0_val = (
        float(params.CornerR) + float(params.BaseBossR)
        + 0.5 + float(params.EspLipW) + float(params.EspClear)
    )
    esp_rx_val = esp_x0_val + float(params.EspW)
    ld_x0_val = (
        esp_rx_val + float(params.EspClear) + float(params.EspLipW)
        + float(params.ModuleGapX) + float(params.LdLipW)
    )
    ld_wall_x_val = ld_x0_val + float(params.LdL)

    fillet_edge_names = []
    for i, edge in enumerate(last_feat.Shape.Edges):
        bb = edge.BoundBox
        if abs(bb.ZMin - floor_z) < 0.05 and abs(bb.ZMax - floor_z) < 0.05:
            # ESP Rear Snap Clips: front (-Y) and back (+Y) root edges at Z = Floor
            if (
                abs(bb.XLength - snap_w_val) < 0.15
                and bb.YLength < 0.1
                and (stem_y_min - 0.2 <= bb.YMin <= stem_y_min + stem_t_val + 0.2)
                and (esp_x0_val + 2.0 <= bb.Center.x <= esp_rx_val - 2.0)
            ):
                fillet_edge_names.append(f"Edge{i + 1}")
            # Secondary Module +X Flex Wall: front (-X) and back (+X) root edges at Z = Floor
            elif (
                abs(bb.YLength - (float(params.LdW) - 4.0)) < 0.2
                and bb.XLength < 0.1
                and (ld_wall_x_val - 0.2 <= bb.XMin <= ld_wall_x_val + float(params.LdWallThick) + 0.2)
            ):
                fillet_edge_names.append(f"Edge{i + 1}")

    if fillet_edge_names:
        fillet = body.newObject("PartDesign::Fillet", f"{prefix}SnapBaseFillet")
        fillet.Base = (last_feat, fillet_edge_names)
        fillet.setExpression("Radius", "Params.SnapFilletR")

    # -------------------------------------------------------------------------
    # D. RECESSED FLOOR LABELS (0.45mm Deep Under Both Modules)
    # -------------------------------------------------------------------------
    esp_label_cx = esp_x0_val + float(params.EspW) / 2.0
    esp_label_cy = float(params.Wall) + 0.2 + float(params.EspL) / 2.0
    add_recessed_floor_label(
        body, f"{prefix}EspFloorLabel", esp_cfg["Label"],
        center_x=esp_label_cx, center_y=esp_label_cy, font_size=3.6
    )

    ld_hdr_reach_val = float(params.LdOutLedge) + float(params.EspTroughW) + 1.05
    ld_window_x_min = ld_x0_val + ld_hdr_reach_val
    ld_window_x_max = ld_wall_x_val - float(params.SnapOverhang) - float(params.SnapFilletR)
    ld_label_cx = 0.5 * (ld_window_x_min + ld_window_x_max)
    ld_label_cy = float(params.Wall) + float(params.IntY) / 2.0
    add_recessed_floor_label(
        body, f"{prefix}ModFloorLabel", mod_cfg["Label"],
        center_x=ld_label_cx, center_y=ld_label_cy, font_size=3.0
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

# =============================================================================
# 2. FULL CLAMSHELL BASE BODY
# =============================================================================
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

# =============================================================================
# 3. CLAMSHELL LID BODY
# =============================================================================
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

# =============================================================================
# 4. PARAMETRIC FAST-ITERATION TEST PLATE BODY
# =============================================================================
test_body = doc.addObject("PartDesign::Body", "TestPlate")
test_xy = next(f for f in test_body.Origin.OriginFeatures if f.Role == "XY_Plane")
test_xz = next(f for f in test_body.Origin.OriginFeatures if f.Role == "XZ_Plane")

add_pd_feature(
    test_body, test_xy, "PartDesign::AdditiveBox", "TestFloor",
    {"x": "Params.CornerR + Params.BaseBossR - 1 mm", "y": "0", "z": "0"},
    {
        "Length": "Params.IntX + 2 * Params.Wall - (Params.CornerR + Params.BaseBossR) - 3 mm",
        "Width": "Params.EspL + Params.Wall + Params.EspRearClearY + 1.8 mm + Params.SnapFilletR + 2 mm",
        "Height": "Params.Floor",
    }
)

add_pd_feature(
    test_body, test_xy, "PartDesign::AdditiveBox", "TestUsbWallStub",
    {"x": "Params.CornerR + Params.BaseBossR + 0.4 mm", "y": "0", "z": "0"},
    {
        "Length": "Params.EspW + 2 * Params.EspLipW + 0.4 mm",
        "Width": "Params.Wall",
        "Height": "Params.Floor + Params.EspShelfH + Params.EspThick + 2.5 mm",
    }
)

add_board_mounts_and_usb(test_body, test_xy, test_xz, prefix="Test_")
test_body.setExpression(".Placement.Base.y", f"-({oy_expr} + 10 mm)")

# =============================================================================
# 5. RECOMPUTE & EXPORT BOTH STEP FILES
# =============================================================================
doc.recompute()
Import.export([assembly], "esp32_ld2410_clamshell.step")
Import.export([test_body], "esp32_ld2410_testplate.step")