import streamlit as st
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Optional, List, Dict
from io import BytesIO
from datetime import datetime

# ---------- Logo & Website Header ----------

LOGO_URL = "https://www.ferasaviation.info/gallery/FA__logo.png?ts=1754692591"
WEBSITE_URL = "https://www.ferasaviation.info"

# ---------- Aircraft presets (update with your real WBM data) ----------

AIRCRAFT_PRESETS: Dict[str, Dict] = {
    "Boeing 787": {
        "label": "Boeing 787",
        "type": "dual_bogie",  # NLG + 4 x MLG bogie scales

        # Real Boeing 787 gear arms (inches from datum)
        "nlg_arm": 268.0,          # Nose Landing Gear
        # MLG bogie positions (forward & aft) – left
        "lmlg_fwd_arm": 1137.30,
        "lmlg_aft_arm": 1194.80,
        # Assume symmetric right main gear
        "rmlg_fwd_arm": 1137.30,
        "rmlg_aft_arm": 1194.80,

        # TODO: Replace these with aircraft-specific WBM data
        "lemac": 830.0,            # placeholder
        "mac_length": 240.0,       # placeholder
    },
    "Boeing 737": {
        "label": "Boeing 737",
        "type": "simple",     # NLG + LMLG + RMLG

        # Values based on your example data (inches from datum)
        "nlg_arm": 93.0,          # Nose Landing Gear arm (in)
        "lmlg_arm": 706.822,      # Main Landing Gear arm (in)
        "rmlg_arm": 706.822,      # Symmetric right MLG

        # LEMAC / MAC here are illustrative – replace with real 737 WBM data
        "lemac": 610.0,           # placeholder
        "mac_length": 130.0,      # placeholder
    },
}

# ---------- Core data structures & logic ----------

@dataclass
class WeighPoint:
    name: str       # e.g. "NLG", "LMLG FWD"
    weight: float   # scale reading (kg or lb)
    arm: float      # distance from datum (same length units everywhere)
    serial: str = ""  # scale pad serial number (optional)


@dataclass
class CGResult:
    total_weight: float
    total_moment: float
    cg_arm: float
    mac_percent: Optional[float] = None


def compute_cg(weigh_points: List[WeighPoint],
               lemac_arm: Optional[float] = None,
               mac_length: Optional[float] = None) -> CGResult:
    """
    Compute CG from a list of weighing points.
    Optionally compute %MAC if LEMAC arm and MAC length are provided.
    """
    if not weigh_points:
        raise ValueError("No weighing points provided.")

    total_weight = sum(p.weight for p in weigh_points)
    if total_weight <= 0:
        raise ValueError("Total weight must be positive.")

    total_moment = sum(p.weight * p.arm for p in weigh_points)
    cg_arm = total_moment / total_weight

    mac_percent = None
    if lemac_arm is not None and mac_length is not None and mac_length > 0:
        mac_percent = (cg_arm - lemac_arm) / mac_length * 100.0

    return CGResult(
        total_weight=total_weight,
        total_moment=total_moment,
        cg_arm=cg_arm,
        mac_percent=mac_percent
    )


def normalise(value: float, min_val: float, max_val: float) -> float:
    """Normalise a value to 0–1 for plotting."""
    if max_val <= min_val:
        return 0.5
    return (value - min_val) / (max_val - min_val)


def draw_aircraft_diagram(
    gear_arms: List[float],
    gear_labels: List[str],
    cg_arm: float,
    lemac_arm: Optional[float] = None,
    mac_length: Optional[float] = None,
):
    """
    Draw a simple 2D side-view diagram of the aircraft with:
    - Fuselage as a bar
    - Arbitrary number of gear positions (NLG, MLG bogies, etc.)
    - MAC span (if given)
    - CG location
    Arms are scaled linearly between min and max arms.
    """

    if not gear_arms:
        raise ValueError("No gear arms provided for diagram.")

    arms = list(gear_arms) + [cg_arm]
    if lemac_arm is not None and mac_length is not None:
        arms.extend([lemac_arm, lemac_arm + mac_length])

    min_arm = min(arms)
    max_arm = max(arms)

    fig, ax = plt.subplots(figsize=(8, 2))

    # Fuselage bar
    ax.hlines(0.5, 0.02, 0.98, linewidth=6)

    # Nose & tail markers (approx at min/max)
    ax.text(0.02, 0.6, "Nose", ha="left", va="bottom", fontsize=8)
    ax.text(0.98, 0.6, "Tail", ha="right", va="bottom", fontsize=8)

    # Gear markers
    gear_y = 0.35
    for i, (arm, label) in enumerate(zip(gear_arms, gear_labels)):
        x = normalise(arm, min_arm, max_arm)
        ax.vlines(x, 0.5, gear_y, linewidth=3)
        ax.scatter([x], [gear_y], s=60)
        # Slight vertical offset between labels to reduce overlap
        label_offset = 0.08 + 0.03 * (i % 2)
        ax.text(x, gear_y - label_offset, label, ha="center", va="top", fontsize=8)

    # MAC region (if available)
    if lemac_arm is not None and mac_length is not None:
        x_lemac = normalise(lemac_arm, min_arm, max_arm)
        x_tlemac = normalise(lemac_arm + mac_length, min_arm, max_arm)
        mac_y = 0.62
        ax.hlines(mac_y, x_lemac, x_tlemac, linewidth=4)
        ax.vlines(x_lemac, mac_y - 0.02, mac_y + 0.02, linewidth=2)
        ax.vlines(x_tlemac, mac_y - 0.02, mac_y + 0.02, linewidth=2)
        ax.text(x_lemac, mac_y + 0.03, "LEMAC", ha="center", va="bottom", fontsize=8)
        ax.text(x_tlemac, mac_y + 0.03, "TEMAC", ha="center", va="bottom", fontsize=8)
        ax.text((x_lemac + x_tlemac) / 2, mac_y + 0.05, "MAC",
                ha="center", va="bottom", fontsize=8)

    # CG marker
    x_cg = normalise(cg_arm, min_arm, max_arm)
    ax.vlines(x_cg, 0.45, 0.75, linestyle="--", linewidth=2)
    ax.scatter([x_cg], [0.75], s=50)
    ax.text(x_cg, 0.78, "CG", ha="center", va="bottom",
            fontsize=9, fontweight="bold")

    # Axis formatting
    ax.set_xlim(0, 1)
    ax.set_ylim(0.1, 0.9)
    ax.axis("off")

    # Annotation of scale (min/max arm)
    ax.text(0.02, 0.15, f"Datum scale: {min_arm:.1f} to {max_arm:.1f}",
            ha="left", va="center", fontsize=8)

    return fig


def draw_cg_envelope_plot(
    min_weight: float,
    max_weight: float,
    fwd_limit: float,
    aft_limit: float,
    as_w: float,
    as_mac: Optional[float],
    corrected_w: float,
    corrected_mac: Optional[float],
):
    """
    Draw a CG envelope diagram: Weight vs %MAC with a simple rectangular envelope.
    Plots as-weighed and corrected CG points if %MAC values are provided.
    """
    if min_weight <= 0 or max_weight <= min_weight or aft_limit <= fwd_limit:
        raise ValueError("Invalid CG envelope limits.")

    fig, ax = plt.subplots(figsize=(4, 4))

    # Envelope rectangle
    env_x = [fwd_limit, fwd_limit, aft_limit, aft_limit, fwd_limit]
    env_y = [min_weight, max_weight, max_weight, min_weight, min_weight]
    ax.plot(env_x, env_y, linestyle="-")
    ax.fill(env_x, env_y, alpha=0.1)

    # As-weighed point
    if as_mac is not None and as_w > 0:
        ax.scatter([as_mac], [as_w], marker="x")
        ax.text(as_mac, as_w, " As-weighed", fontsize=8, va="bottom", ha="left")

    # Corrected point
    if corrected_mac is not None and corrected_w > 0:
        ax.scatter([corrected_mac], [corrected_w], marker="o")
        ax.text(corrected_mac, corrected_w, " Corrected", fontsize=8, va="top", ha="left")

    ax.set_xlabel("% MAC")
    ax.set_ylabel("Weight")
    ax.set_title("CG Envelope")

    # Sensible x/y limits padding
    x_min = min(fwd_limit, aft_limit) - 2
    x_max = max(fwd_limit, aft_limit) + 2
    ax.set_xlim(x_min, x_max)

    y_pad = 0.05 * (max_weight - min_weight)
    ax.set_ylim(min_weight - y_pad, max_weight + y_pad)

    ax.grid(True, linestyle="--", linewidth=0.5)
    return fig


# ---------- PDF report generation ----------

def build_pdf_report(
    result: CGResult,
    points: List[WeighPoint],
    weight_unit: str,
    arm_unit: str,
    lemac_arm: Optional[float],
    mac_length: Optional[float],
    # metadata fields:
    msn: str,
    operator: str,
    registration: str,
    aircraft_type: str,
    weighing_location: str,
    scales_cal_date: str,
    weighing_date: str,
    wbm_reference: str,
    equipment_model: str,
    equipment_serial: str,
    pitch_attitude_deg: float,
    pitch_correction: float,
    subtractions: List[Dict],
    additions: List[Dict],
    weighed_by: str,
    weighed_by_date: str,
    checked_by: str,
    checked_by_date: str,
    approved_by: str,
    approved_by_date: str,
    config_notes: str,
    # CG envelope:
    env_min_weight: float,
    env_max_weight: float,
    env_fwd_limit: float,
    env_aft_limit: float,
    final_mac_percent: Optional[float],
    # CG diagrams:
    cg_diagram_png: Optional[BytesIO] = None,
    cg_envelope_png: Optional[BytesIO] = None,
) -> BytesIO:
    """
    Build a PDF weight & balance report and return it as an in-memory buffer.
    Includes logo, aircraft details, weighing data, CG diagram on the same page,
    CG envelope plot, adjustments, notes, and signature blocks.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    import requests

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    margin_x = 40
    y = height - 40

    # --- Logo at top ---
    logo_height = 40
    logo_width = 120
    try:
        resp = requests.get(LOGO_URL, timeout=5)
        resp.raise_for_status()
        logo_img = ImageReader(BytesIO(resp.content))
        c.drawImage(
            logo_img,
            margin_x,
            y - logo_height,
            width=logo_width,
            height=logo_height,
            preserveAspectRatio=True,
            mask='auto'
        )
    except Exception:
        # If logo fails, we just skip it
        pass

    # Header text to the right of logo, fixed as "7x7"
    c.setFont("Helvetica-Bold", 16)
    c.drawString(
        margin_x + logo_width + 20,
        y - 10,
        "Boeing 7x7 Weight & Balance Report"
    )

    y -= (logo_height + 20)

    # Website & timestamp
    c.setFont("Helvetica", 9)
    c.drawString(margin_x, y, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 12
    c.drawString(margin_x, y, f"Website: {WEBSITE_URL}")
    y -= 20

    # --- Aircraft & weighing details (2-column layout) ---
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin_x, y, "Aircraft & Weighing Details")
    y -= 16

    c.setFont("Helvetica", 10)

    details = [
        ("Operator", operator or "-"),
        ("Aircraft Type", aircraft_type or "-"),
        ("Registration", registration or "-"),
        ("MSN", msn or "-"),
        ("Weighing location", weighing_location or "-"),
        ("Weighing Date", weighing_date or "-"),
        ("Scales Calibration Date", scales_cal_date or "-"),
        ("WBM reference", wbm_reference or "-"),
        ("Equipment model", equipment_model or "-"),
        ("Equipment serial", equipment_serial or "-"),
    ]

    pitch_str = f"{pitch_attitude_deg:.2f}°" if pitch_attitude_deg else "-"
    corr_str = f"{pitch_correction:.2f} {arm_unit}" if pitch_correction else "0"
    details.extend([
        ("Pitch attitude during weighing", pitch_str),
        ("Pitch correction applied to CG", corr_str),
    ])

    left_x = margin_x
    right_x = margin_x + 260
    row_height = 12

    num_rows = (len(details) + 1) // 2
    for i, (label, value) in enumerate(details):
        row = i // 2
        col = i % 2
        y_row = y - row * row_height
        x = left_x if col == 0 else right_x
        c.drawString(x, y_row, f"{label}: {value}")
    y = y - num_rows * row_height - 8

    # --- Compute adjustments for summary ---
    as_w = result.total_weight
    as_m = result.total_moment
    as_cg = result.cg_arm

    sum_sub_w = sum(item["weight"] for item in subtractions)
    sum_sub_m = sum(item["weight"] * item["arm"] for item in subtractions)
    sum_add_w = sum(item["weight"] for item in additions)
    sum_add_m = sum(item["weight"] * item["arm"] for item in additions)

    # Apply pitch correction as delta in CG arm
    pitch_corrected_m = as_m + pitch_correction * as_w

    corrected_weight = as_w - sum_sub_w + sum_add_w
    corrected_moment = pitch_corrected_m - sum_sub_m + sum_add_m
    corrected_cg = corrected_moment / corrected_weight if corrected_weight > 0 else as_cg

    corrected_mac_percent = final_mac_percent

    # --- Summary ---
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin_x, y, "Summary")
    y -= 16

    c.setFont("Helvetica", 10)
    c.drawString(margin_x, y, f"As-weighed weight: {as_w:,.1f} {weight_unit}")
    y -= 12
    c.drawString(margin_x, y, f"As-weighed CG arm: {as_cg:.2f} {arm_unit} from datum")
    y -= 12

    if pitch_correction:
        c.drawString(
            margin_x,
            y,
            f"Pitch-corrected moment applied: ΔCG = {pitch_correction:.2f} {arm_unit}"
        )
        y -= 12

    c.drawString(margin_x, y, f"Total subtractions: {sum_sub_w:,.1f} {weight_unit}")
    y -= 12
    c.drawString(margin_x, y, f"Total additions: {sum_add_w:,.1f} {weight_unit}")
    y -= 12

    c.drawString(margin_x, y, f"Final aircraft weight: {corrected_weight:,.1f} {weight_unit}")
    y -= 12
    c.drawString(margin_x, y, f"Final CG arm: {corrected_cg:.2f} {arm_unit} from datum")
    y -= 12

    if corrected_mac_percent is not None:
        c.drawString(margin_x, y, f"Final CG position: {corrected_mac_percent:.2f} % MAC")
        y -= 16
    else:
        y -= 8

    # --- Gear Weighing Data Table ---
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin_x, y, "Gear Weighing Data")
    y -= 16

    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin_x, y, "Point")
    c.drawString(margin_x + 90, y, "Scale S/N")
    c.drawString(margin_x + 200, y, f"Weight ({weight_unit})")
    c.drawString(margin_x + 320, y, f"Arm ({arm_unit})")
    c.drawString(margin_x + 420, y, "Moment")
    y -= 12

    c.setFont("Helvetica", 10)
    for p in points:
        moment = p.weight * p.arm
        c.drawString(margin_x, y, p.name)
        c.drawString(margin_x + 90, y, p.serial or "-")
        c.drawRightString(margin_x + 260, y, f"{p.weight:,.1f}")
        c.drawRightString(margin_x + 380, y, f"{p.arm:.2f}")
        c.drawRightString(margin_x + 500, y, f"{moment:,.1f}")
        y -= 12
        if y < 200:
            break

    y -= 8
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(
        margin_x,
        y,
        "Note: This report is generated by the Feras Aviation CG Calculator tool. "
        "Verify against approved Weight & Balance data and procedures."
    )
    y -= 20

    # --- Adjustments tables: Subtractions & Additions ---
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin_x, y, "Adjustments")
    y -= 16

    # Subtractions
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin_x, y, "Subtractions (items present during weighing but not in final weight)")
    y -= 12
    c.setFont("Helvetica-Bold", 9)
    c.drawString(margin_x, y, "Item")
    c.drawString(margin_x + 220, y, f"Weight ({weight_unit})")
    c.drawString(margin_x + 320, y, f"Arm ({arm_unit})")
    c.drawString(margin_x + 420, y, "Moment")
    y -= 12

    c.setFont("Helvetica", 9)
    if subtractions:
        for item in subtractions:
            moment = item["weight"] * item["arm"]
            c.drawString(margin_x, y, item["description"] or "-")
            c.drawRightString(margin_x + 280, y, f"{item['weight']:,.1f}")
            c.drawRightString(margin_x + 380, y, f"{item['arm']:.2f}")
            c.drawRightString(margin_x + 500, y, f"{moment:,.1f}")
            y -= 11
            if y < 180:
                break
    else:
        c.drawString(margin_x, y, "(None)")
        y -= 12

    y -= 8

    # Additions
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin_x, y, "Additions (items not present during weighing but included in final weight)")
    y -= 12
    c.setFont("Helvetica-Bold", 9)
    c.drawString(margin_x, y, "Item")
    c.drawString(margin_x + 220, y, f"Weight ({weight_unit})")
    c.drawString(margin_x + 320, y, f"Arm ({arm_unit})")
    c.drawString(margin_x + 420, y, "Moment")
    y -= 12

    c.setFont("Helvetica", 9)
    if additions:
        for item in additions:
            moment = item["weight"] * item["arm"]
            c.drawString(margin_x, y, item["description"] or "-")
            c.drawRightString(margin_x + 280, y, f"{item['weight']:,.1f}")
            c.drawRightString(margin_x + 380, y, f"{item['arm']:.2f}")
            c.drawRightString(margin_x + 500, y, f"{moment:,.1f}")
            y -= 11
            if y < 160:
                break
    else:
        c.drawString(margin_x, y, "(None)")
        y -= 12

    y -= 10

    # --- CG diagram on same page (side view) ---
    if cg_diagram_png is not None:
        from reportlab.lib.utils import ImageReader
        img = ImageReader(cg_diagram_png)
        img_width_px, img_height_px = img.getSize()

        max_width = width - 2 * margin_x
        # Reserve some space at the bottom for envelope + signatures
        max_height = max(y - 180, 60)

        scale = min(max_width / img_width_px, max_height / img_height_px)
        draw_width = img_width_px * scale
        draw_height = img_height_px * scale

        x_pos = (width - draw_width) / 2
        y_pos = max(y - draw_height, 200)

        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin_x, y, "CG Diagram (Side View)")
        c.drawImage(
            img,
            x_pos,
            y_pos,
            width=draw_width,
            height=draw_height,
            preserveAspectRatio=True,
            mask='auto'
        )
        y = y_pos - 10
    else:
        y -= 10

    # --- CG Envelope diagram (Weight vs %MAC) ---
    if cg_envelope_png is not None and y > 150:
        from reportlab.lib.utils import ImageReader
        img = ImageReader(cg_envelope_png)
        img_width_px, img_height_px = img.getSize()

        max_width = width - 2 * margin_x
        max_height = max(y - 120, 60)

        scale = min(max_width / img_width_px, max_height / img_height_px)
        draw_width = img_width_px * scale
        draw_height = img_height_px * scale

        x_pos = (width - draw_width) / 2
        y_pos = max(y - draw_height, 120)

        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin_x, y, "CG Envelope (Weight vs %MAC)")
        c.drawImage(
            img,
            x_pos,
            y_pos,
            width=draw_width,
            height=draw_height,
            preserveAspectRatio=True,
            mask='auto'
        )
        y = y_pos - 10
    else:
        y -= 10

    # --- Configuration / Notes ---
    if config_notes:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(margin_x, y, "Configuration / Notes")
        y -= 12
        c.setFont("Helvetica", 9)

        max_chars = 90
        notes_lines = []
        for line in config_notes.split("\n"):
            while len(line) > max_chars:
                notes_lines.append(line[:max_chars])
                line = line[max_chars:]
            notes_lines.append(line)

        for line in notes_lines:
            c.drawString(margin_x, y, line)
            y -= 11
            if y < 80:
                break

    # --- Certification statement ---
    y = max(y, 80)
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(
        margin_x,
        y,
        "Certified that this aircraft has been weighed in accordance with the applicable "
        "Weight & Balance Manual and procedures."
    )
    y -= 12
    c.drawString(
        margin_x,
        y,
        "This report is issued by Feras Aviation Technical Services Ltd for engineering support purposes."
    )

    # --- Signature blocks at bottom of page ---
    sig_y = 40
    col_width = (width - 2 * margin_x) / 3.0

    def draw_signature_block(x: float, label: str, name: str, date: str):
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x, sig_y + 28, label)
        # Line for signature
        c.line(x, sig_y + 18, x + col_width - 20, sig_y + 18)
        c.setFont("Helvetica", 9)
        if name:
            c.drawString(x, sig_y + 6, f"Name: {name}")
        if date:
            c.drawString(x, sig_y - 6, f"Date: {date}")

    draw_signature_block(margin_x, "Weighed by", weighed_by, weighed_by_date)
    draw_signature_block(margin_x + col_width, "Checked by", checked_by, checked_by_date)
    draw_signature_block(margin_x + 2 * col_width, "Approved by", approved_by, approved_by_date)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


# ---------- Streamlit UI ----------

st.set_page_config(
    page_title="Boeing 7x7 CG Calculator (737 / 787)",
    layout="wide",
)

st.title("Boeing 7x7 Weighing – Centre of Gravity Calculator")

st.markdown(
    """
Enter your **scale readings**, **arms from datum**, aircraft details, envelope limits, and adjustments.  
The app computes as-weighed and corrected weight & CG, shows a side-view diagram and a CG envelope plot,
and generates a comprehensive PDF Weight & Balance report (with diagrams and sign-off on page 1).

> Presets are for engineering support only – always verify against your approved W&B data.
"""
)

# Sidebar: logo, link, units
with st.sidebar:
    st.image(LOGO_URL, use_column_width=True)
    st.markdown(
        f"""
        <div style='text-align: center; margin-top: 10px;'>
            <a href='{WEBSITE_URL}' target='_blank'
               style='text-decoration: none; font-size: 16px;'>
                🌐 Visit Our Website
            </a>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")

    st.header("Units & Info")
    weight_unit = st.selectbox("Weight unit", ["kg", "lb"], index=0)
    arm_unit = st.selectbox("Arm / distance unit", ["in", "m"], index=0)
    st.markdown(
        """
        **Reminder**  
        • Preset arms are in **inches** – keep arm unit on *in* unless you convert them  
        • Use arms from the *same datum*  
        • Replace presets with your approved WBM data for each type  
        """
    )

# ---------- Aircraft selection (787 / 737) ----------

st.subheader("Aircraft Selection")

aircraft_model = st.selectbox(
    "Aircraft model",
    list(AIRCRAFT_PRESETS.keys()),
    index=0,
    help="Select aircraft model to load default arms and MAC data."
)
preset = AIRCRAFT_PRESETS[aircraft_model]

st.caption(
    "Preset arms and MAC values are illustrative (except where you provided real data). "
    "Always confirm against your Weight & Balance Manual."
)

# ---------- Aircraft & weighing details ----------

st.subheader("Aircraft & Weighing Details")

dcol1, dcol2, dcol3 = st.columns(3)
with dcol1:
    operator = st.text_input("Operator", value="")
    aircraft_type = st.text_input("Aircraft type", value=preset["label"])
with dcol2:
    registration = st.text_input("Registration", value="")
    msn = st.text_input("MSN", value="")
with dcol3:
    weighing_location = st.text_input("Weighing location", value="")
    scales_cal_date = st.text_input("Scales calibration date", value="")
    weighing_date = st.text_input("Weighing date", value=datetime.now().strftime("%Y-%m-%d"))

wbm_reference = st.text_input(
    "WBM reference (document no & revision)",
    value="",
    help="e.g. B787-WBM-12345 Rev 3"
)

st.markdown("---")

# ---------- Equipment / scales info ----------

st.subheader("Equipment / Scales Information")

ecol1, ecol2 = st.columns(2)
with ecol1:
    equipment_model = st.text_input("Equipment model (scale type)", value="")
with ecol2:
    equipment_serial = st.text_input("Equipment serial / ID", value="")

st.markdown("---")

# ---------- Sign-off ----------

st.subheader("Sign-off")

scol1, scol2, scol3 = st.columns(3)
with scol1:
    weighed_by = st.text_input("Weighed by (name)", value="")
    weighed_by_date = st.text_input("Weighed by - date", value=weighing_date)
with scol2:
    checked_by = st.text_input("Checked by (name)", value="")
    checked_by_date = st.text_input("Checked by - date", value=weighing_date)
with scol3:
    approved_by = st.text_input("Approved by (name)", value="")
    approved_by_date = st.text_input("Approved by - date", value=weighing_date)

st.markdown("---")

# ---------- Weighing Inputs ----------

st.subheader("Weighing Inputs")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Gear Weights (measured)")

    if preset["type"] == "dual_bogie":
        # 787: NLG + 4 bogies
        nlg_w = st.number_input(f"NLG weight ({weight_unit})", min_value=0.0, value=30000.0, step=100.0)
        lmlg_fwd_w = st.number_input(f"LMLG FWD weight ({weight_unit})", min_value=0.0, value=60000.0, step=100.0)
        lmlg_aft_w = st.number_input(f"LMLG AFT weight ({weight_unit})", min_value=0.0, value=60000.0, step=100.0)
        rmlg_fwd_w = st.number_input(f"RMLG FWD weight ({weight_unit})", min_value=0.0, value=60000.0, step=100.0)
        rmlg_aft_w = st.number_input(f"RMLG AFT weight ({weight_unit})", min_value=0.0, value=60000.0, step=100.0)
    else:
        # 737: NLG + LMLG + RMLG
        nlg_w = st.number_input(f"NLG weight ({weight_unit})", min_value=0.0, value=15000.0, step=100.0)
        lmlg_w = st.number_input(f"LMLG weight ({weight_unit})", min_value=0.0, value=40000.0, step=100.0)
        rmlg_w = st.number_input(f"RMLG weight ({weight_unit})", min_value=0.0, value=40000.0, step=100.0)

with col2:
    st.markdown("### Gear Arms & Scale Serials (from datum)")

    if preset["type"] == "dual_bogie":
        nlg_arm = st.number_input(
            f"NLG arm ({arm_unit})",
            value=preset["nlg_arm"],
            step=1.0,
            help="From WBM. Provided value: 268 in for B787."
        )
        nlg_serial = st.text_input("NLG scale serial", value="")

        lmlg_fwd_arm = st.number_input(
            f"LMLG FWD arm ({arm_unit})",
            value=preset["lmlg_fwd_arm"],
            step=1.0,
            help="From WBM. Provided value: 1137.30 in for B787."
        )
        lmlg_fwd_serial = st.text_input("LMLG FWD scale serial", value="")

        lmlg_aft_arm = st.number_input(
            f"LMLG AFT arm ({arm_unit})",
            value=preset["lmlg_aft_arm"],
            step=1.0,
            help="From WBM. Provided value: 1194.80 in for B787."
        )
        lmlg_aft_serial = st.text_input("LMLG AFT scale serial", value="")

        rmlg_fwd_arm = st.number_input(
            f"RMLG FWD arm ({arm_unit})",
            value=preset["rmlg_fwd_arm"],
            step=1.0,
            help="Symmetric to LMLG FWD."
        )
        rmlg_fwd_serial = st.text_input("RMLG FWD scale serial", value="")

        rmlg_aft_arm = st.number_input(
            f"RMLG AFT arm ({arm_unit})",
            value=preset["rmlg_aft_arm"],
            step=1.0,
            help="Symmetric to LMLG AFT."
        )
        rmlg_aft_serial = st.text_input("RMLG AFT scale serial", value="")
    else:
        nlg_arm = st.number_input(
            f"NLG arm ({arm_unit})",
            value=preset["nlg_arm"],
            step=1.0,
            help="From WBM. Example: 93 in for B737."
        )
        nlg_serial = st.text_input("NLG scale serial", value="")

        lmlg_arm = st.number_input(
            f"LMLG arm ({arm_unit})",
            value=preset["lmlg_arm"],
            step=1.0,
            help="From WBM. Example: 706.822 in for B737."
        )
        lmlg_serial = st.text_input("LMLG scale serial", value="")

        rmlg_arm = st.number_input(
            f"RMLG arm ({arm_unit})",
            value=preset["rmlg_arm"],
            step=1.0,
            help="From WBM. Example: 706.822 in for B737."
        )
        rmlg_serial = st.text_input("RMLG scale serial", value="")

st.markdown("---")

# ---------- MAC / CG Envelope Reference ----------

st.subheader("MAC / CG Envelope Reference (optional)")

col3, col4 = st.columns(2)
with col3:
    lemac_arm = st.number_input(
        f"LEMAC arm ({arm_unit})",
        value=preset["lemac"],
        step=1.0,
        help="Leading edge of MAC from same datum. Replace with real data for each type."
    )
with col4:
    mac_length = st.number_input(
        f"MAC length ({arm_unit})",
        value=preset["mac_length"],
        step=0.1,
        help="Mean aerodynamic chord length. Replace with real data for each type."
    )

st.markdown("---")

# ---------- CG Envelope Limits (for plot) ----------

st.subheader("CG Envelope Limits (for Weight vs %MAC plot) – optional")

env_col1, env_col2 = st.columns(2)
with env_col1:
    env_min_weight = st.number_input(
        f"Envelope minimum weight ({weight_unit})",
        min_value=0.0,
        value=0.0,
        step=1000.0,
        help="Lowest weight for the CG envelope. Leave as 0 if not used."
    )
    env_fwd_limit = st.number_input(
        "Forward CG limit (% MAC)",
        value=0.0,
        step=0.1,
        help="Forward limit of CG envelope in %MAC. Must be less than aft limit."
    )
with env_col2:
    env_max_weight = st.number_input(
        f"Envelope maximum weight ({weight_unit})",
        min_value=0.0,
        value=0.0,
        step=1000.0,
        help="Highest weight for the CG envelope."
    )
    env_aft_limit = st.number_input(
        "Aft CG limit (% MAC)",
        value=0.0,
        step=0.1,
        help="Aft limit of CG envelope in %MAC."
    )

st.caption(
    "If envelope limits are left as zero or invalid (min >= max, fwd >= aft), "
    "the CG envelope plot will be skipped."
)

st.markdown("---")

# ---------- Pitch & Adjustments ----------

st.subheader("Pitch & Adjustments")

pcol1, pcol2 = st.columns(2)
with pcol1:
    pitch_attitude_deg = st.number_input(
        "Pitch attitude during weighing (deg)",
        value=0.0,
        step=0.1,
        help="Positive = nose up. Recorded for traceability; not used directly in CG math."
    )
with pcol2:
    pitch_correction = st.number_input(
        f"Pitch correction to CG (Δarm in {arm_unit})",
        value=0.0,
        step=0.01,
        help="Manual CG arm correction applied after weighing (e.g. +0.65 in)."
    )

st.markdown("### Subtractions & Additions")

with st.expander("Subtractions (items present during weighing but not in final weight)", expanded=False):
    n_sub = st.number_input(
        "Number of subtraction items",
        min_value=0, max_value=10, value=0, step=1, key="n_sub_items"
    )
    subtractions: List[Dict] = []
    for i in range(int(n_sub)):
        dcol1, dcol2, dcol3 = st.columns([2, 1, 1])
        desc = dcol1.text_input("Item description", key=f"sub_desc_{i}")
        w = dcol2.number_input(f"Weight ({weight_unit})", min_value=0.0, value=0.0, step=1.0, key=f"sub_w_{i}")
        arm = dcol3.number_input(f"Arm ({arm_unit})", value=0.0, step=0.1, key=f"sub_arm_{i}")
        if desc or w != 0:
            subtractions.append({"description": desc, "weight": w, "arm": arm})

with st.expander("Additions (items not present during weighing but included in final weight)", expanded=False):
    n_add = st.number_input(
        "Number of addition items",
        min_value=0, max_value=10, value=0, step=1, key="n_add_items"
    )
    additions: List[Dict] = []
    for i in range(int(n_add)):
        dcol1, dcol2, dcol3 = st.columns([2, 1, 1])
        desc = dcol1.text_input("Item description", key=f"add_desc_{i}")
        w = dcol2.number_input(f"Weight ({weight_unit})", min_value=0.0, value=0.0, step=1.0, key=f"add_w_{i}")
        arm = dcol3.number_input(f"Arm ({arm_unit})", value=0.0, step=0.1, key=f"add_arm_{i}")
        if desc or w != 0:
            additions.append({"description": desc, "weight": w, "arm": arm})

st.markdown("---")

# ---------- Configuration Notes ----------

st.subheader("Configuration / Notes")

config_notes = st.text_area(
    "Configuration & remarks (fuel state, water, lavs, flaps, attitude, etc.)",
    value="",
    help="Free-text notes for aircraft configuration during weighing.",
    height=120,
)

st.markdown("---")

# ---------- Calculate ----------

calculate = st.button("Calculate CG", type="primary")

if calculate:
    try:
        # Build weighing points list depending on aircraft layout
        if preset["type"] == "dual_bogie":
            points: List[WeighPoint] = [
                WeighPoint("NLG", nlg_w, nlg_arm, nlg_serial),
                WeighPoint("LMLG FWD", lmlg_fwd_w, lmlg_fwd_arm, lmlg_fwd_serial),
                WeighPoint("LMLG AFT", lmlg_aft_w, lmlg_aft_arm, lmlg_aft_serial),
                WeighPoint("RMLG FWD", rmlg_fwd_w, rmlg_fwd_arm, rmlg_fwd_serial),
                WeighPoint("RMLG AFT", rmlg_aft_w, rmlg_aft_arm, rmlg_aft_serial),
            ]
            gear_arms = [nlg_arm, lmlg_fwd_arm, lmlg_aft_arm, rmlg_fwd_arm, rmlg_aft_arm]
            gear_labels = ["NLG", "LMLG FWD", "LMLG AFT", "RMLG FWD", "RMLG AFT"]
        else:
            points = [
                WeighPoint("NLG", nlg_w, nlg_arm, nlg_serial),
                WeighPoint("LMLG", lmlg_w, lmlg_arm, lmlg_serial),
                WeighPoint("RMLG", rmlg_w, rmlg_arm, rmlg_serial),
            ]
            gear_arms = [nlg_arm, lmlg_arm, rmlg_arm]
            gear_labels = ["NLG", "LMLG", "RMLG"]

        result = compute_cg(points, lemac_arm=lemac_arm, mac_length=mac_length)

        # Compute adjustment effects
        as_w = result.total_weight
        as_m = result.total_moment
        as_cg = result.cg_arm

        sum_sub_w = sum(item["weight"] for item in subtractions)
        sum_sub_m = sum(item["weight"] * item["arm"] for item in subtractions)
        sum_add_w = sum(item["weight"] for item in additions)
        sum_add_m = sum(item["weight"] * item["arm"] for item in additions)

        pitch_corrected_m = as_m + pitch_correction * as_w

        corrected_weight = as_w - sum_sub_w + sum_add_w
        corrected_moment = pitch_corrected_m - sum_sub_m + sum_add_m
        corrected_cg = corrected_moment / corrected_weight if corrected_weight > 0 else as_cg

        # As-weighed & corrected %MAC
        as_mac_percent = None
        if lemac_arm is not None and mac_length is not None and mac_length > 0:
            as_mac_percent = (as_cg - lemac_arm) / mac_length * 100.0

        corrected_mac_percent = None
        if lemac_arm is not None and mac_length is not None and mac_length > 0 and corrected_weight > 0:
            corrected_mac_percent = (corrected_cg - lemac_arm) / mac_length * 100.0

        res_col1, res_col2 = st.columns([1, 1.3])

        cg_buffer = None
        env_buffer = None

        with res_col2:
            st.markdown("## Aircraft CG Diagram (Side View)")
            fig = draw_aircraft_diagram(
                gear_arms=gear_arms,
                gear_labels=gear_labels,
                cg_arm=corrected_cg,  # show final corrected CG on diagram
                lemac_arm=lemac_arm,
                mac_length=mac_length,
            )
            st.pyplot(fig)

            cg_buffer = BytesIO()
            fig.savefig(cg_buffer, format="png", bbox_inches="tight")
            cg_buffer.seek(0)

            # CG Envelope plot (if limits are valid and %MAC available)
            if (
                env_min_weight > 0
                and env_max_weight > env_min_weight
                and env_aft_limit > env_fwd_limit
                and (as_mac_percent is not None or corrected_mac_percent is not None)
            ):
                st.markdown("## CG Envelope (Weight vs %MAC)")
                fig_env = draw_cg_envelope_plot(
                    min_weight=env_min_weight,
                    max_weight=env_max_weight,
                    fwd_limit=env_fwd_limit,
                    aft_limit=env_aft_limit,
                    as_w=as_w,
                    as_mac=as_mac_percent,
                    corrected_w=corrected_weight,
                    corrected_mac=corrected_mac_percent,
                )
                st.pyplot(fig_env)

                env_buffer = BytesIO()
                fig_env.savefig(env_buffer, format="png", bbox_inches="tight")
                env_buffer.seek(0)
            else:
                st.info("CG envelope plot not generated – check envelope limits and MAC inputs if you want this diagram.")

        with res_col1:
            st.markdown("## Results")

            st.metric(
                label=f"As-weighed total weight ({weight_unit})",
                value=f"{as_w:,.1f}"
            )
            st.metric(
                label=f"As-weighed CG arm ({arm_unit} from datum)",
                value=f"{as_cg:.2f}"
            )

            st.metric(
                label=f"Corrected weight ({weight_unit})",
                value=f"{corrected_weight:,.1f}"
            )
            st.metric(
                label=f"Corrected CG arm ({arm_unit} from datum)",
                value=f"{corrected_cg:.2f}"
            )

            if as_mac_percent is not None:
                st.metric(
                    label="As-weighed CG (% MAC)",
                    value=f"{as_mac_percent:.2f} %"
                )

            if corrected_mac_percent is not None:
                st.metric(
                    label="Corrected CG (% MAC)",
                    value=f"{corrected_mac_percent:.2f} %"
                )
                st.caption("Check against your approved CG envelope for this aircraft type.")

            st.markdown("### Weighing Moments")
            st.table({
                "Point": [p.name for p in points],
                "Scale S/N": [p.serial or "-" for p in points],
                f"Weight ({weight_unit})": [p.weight for p in points],
                f"Arm ({arm_unit})": [p.arm for p in points],
                "Moment": [p.weight * p.arm for p in points],
            })

            if subtractions or additions or pitch_correction:
                st.markdown("### Adjustments Summary")
                st.write(f"Total subtractions: {sum_sub_w:,.1f} {weight_unit}")
                st.write(f"Total additions: {sum_add_w:,.1f} {weight_unit}")
                st.write(f"Pitch correction applied: {pitch_correction:.2f} {arm_unit}")

            # ---- PDF download button ----
            pdf_buffer = build_pdf_report(
                result=result,
                points=points,
                weight_unit=weight_unit,
                arm_unit=arm_unit,
                lemac_arm=lemac_arm,
                mac_length=mac_length,
                msn=msn,
                operator=operator,
                registration=registration,
                aircraft_type=aircraft_type,
                weighing_location=weighing_location,
                scales_cal_date=scales_cal_date,
                weighing_date=weighing_date,
                wbm_reference=wbm_reference,
                equipment_model=equipment_model,
                equipment_serial=equipment_serial,
                pitch_attitude_deg=pitch_attitude_deg,
                pitch_correction=pitch_correction,
                subtractions=subtractions,
                additions=additions,
                weighed_by=weighed_by,
                weighed_by_date=weighed_by_date,
                checked_by=checked_by,
                checked_by_date=checked_by_date,
                approved_by=approved_by,
                approved_by_date=approved_by_date,
                config_notes=config_notes,
                env_min_weight=env_min_weight,
                env_max_weight=env_max_weight,
                env_fwd_limit=env_fwd_limit,
                env_aft_limit=env_aft_limit,
                final_mac_percent=corrected_mac_percent,
                cg_diagram_png=cg_buffer,
                cg_envelope_png=env_buffer,
            )

            st.download_button(
                label="📄 Download PDF Weight & Balance Report",
                data=pdf_buffer,
                file_name=f"wb_report_{aircraft_model.replace(' ', '')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf",
            )

    except Exception as e:
        st.error(f"Error during calculation: {e}")
else:
    st.info("Select aircraft type, enter aircraft details, weighing data, envelope limits, and adjustments, then click **Calculate CG**.")
