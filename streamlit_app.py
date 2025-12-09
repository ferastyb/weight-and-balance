import streamlit as st
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Optional, List
from io import BytesIO
from datetime import datetime

# ---------- Logo & Website Header ----------

LOGO_URL = "https://www.ferasaviation.info/gallery/FA__logo.png?ts=1754692591"
WEBSITE_URL = "https://www.ferasaviation.info"

# ---------- Aircraft presets (update with your real WBM data) ----------

# NOTE:
# • 737 values below use your provided example:
#   NLG arm = 93 in, MLG arm = 706.822 in (from datum).
# • 787 gear arms below are based on your provided data:
#   NLG = 268 in, MLG FWD = 1137.30 in, MLG AFT = 1194.80 in (from datum).
# • LEMAC / MAC for both types are placeholders – replace with WBM data.

AIRCRAFT_PRESETS = {
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

        # Values below based on your example data (inches from datum)
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


@dataclass
class CGResult:
    total_weight: float
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
    weighing_place: str,
    scales_cal_date: str,
    weighing_date: str,
    # CG diagram image buffer:
    cg_diagram_png: Optional[BytesIO] = None,
) -> BytesIO:
    """
    Build a PDF weight & balance report and return it as an in-memory buffer.
    Includes logo, aircraft details, weighing data, and CG diagram on the same page.
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

    # Header text to the right of logo, using selected aircraft_type
    header_type = aircraft_type or "Boeing"
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin_x + logo_width + 20, y - 10, f"{header_type} Weight & Balance Report")

    y -= (logo_height + 20)

    # Website & timestamp
    c.setFont("Helvetica", 9)
    c.drawString(margin_x, y, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 12
    c.drawString(margin_x, y, f"Website: {WEBSITE_URL}")
    y -= 20

    # --- Aircraft & weighing details ---
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin_x, y, "Aircraft & Weighing Details")
    y -= 16

    c.setFont("Helvetica", 10)

    def draw_detail(label: str, value: str):
        nonlocal y
        c.drawString(margin_x, y, f"{label}: {value}")
        y -= 12

    draw_detail("Operator", operator or "-")
    draw_detail("Aircraft Type", aircraft_type or "-")
    draw_detail("Registration", registration or "-")
    draw_detail("MSN", msn or "-")
    draw_detail("Weighing Location", weighing_place or "-")
    draw_detail("Weighing Date", weighing_date or "-")
    draw_detail("Scales Calibration Date", scales_cal_date or "-")

    y -= 8

    # --- Summary ---
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin_x, y, "Summary")
    y -= 16

    c.setFont("Helvetica", 10)
    c.drawString(margin_x, y, f"Total weight: {result.total_weight:,.1f} {weight_unit}")
    y -= 12
    c.drawString(margin_x, y, f"CG arm: {result.cg_arm:.2f} {arm_unit} from datum")
    y -= 12

    if result.mac_percent is not None and lemac_arm is not None and mac_length is not None:
        c.drawString(margin_x, y, f"CG position: {result.mac_percent:.2f} % MAC")
        y -= 12
        c.drawString(margin_x, y, f"LEMAC: {lemac_arm:.2f} {arm_unit}   MAC length: {mac_length:.2f} {arm_unit}")
        y -= 18
    else:
        y -= 8

    # --- Table header ---
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin_x, y, "Gear Weighing Data")
    y -= 16

    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin_x, y, "Point")
    c.drawString(margin_x + 100, y, f"Weight ({weight_unit})")
    c.drawString(margin_x + 220, y, f"Arm ({arm_unit})")
    c.drawString(margin_x + 340, y, "Moment")
    y -= 12

    c.setFont("Helvetica", 10)
    for p in points:
        moment = p.weight * p.arm
        c.drawString(margin_x, y, p.name)
        c.drawRightString(margin_x + 180, y, f"{p.weight:,.1f}")
        c.drawRightString(margin_x + 300, y, f"{p.arm:.2f}")
        c.drawRightString(margin_x + 430, y, f"{moment:,.1f}")
        y -= 12
        # If we get too low, we stop table early to leave room for note + diagram
        if y < 160:
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

    # --- CG diagram on same page (if provided) ---
    if cg_diagram_png is not None:
        from reportlab.lib.utils import ImageReader
        img = ImageReader(cg_diagram_png)
        img_width_px, img_height_px = img.getSize()

        max_width = width - 2 * margin_x
        # Use remaining vertical space above bottom margin (40)
        max_height = max(y - 40, 60)

        scale = min(max_width / img_width_px, max_height / img_height_px)
        draw_width = img_width_px * scale
        draw_height = img_height_px * scale

        x_pos = (width - draw_width) / 2
        y_pos = max(y - draw_height, 40)

        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin_x, y, "CG Diagram")
        c.drawImage(
            img,
            x_pos,
            y_pos,
            width=draw_width,
            height=draw_height,
            preserveAspectRatio=True,
            mask='auto'
        )

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


# ---------- Streamlit UI ----------

st.set_page_config(
    page_title="Boeing CG Calculator (737 / 787)",
    layout="wide",
)

st.title("Boeing 737 / 787 Weighing – Centre of Gravity Calculator")

st.markdown(
    """
Enter your **scale readings**, **arms from datum**, and aircraft details.  
The app will compute total weight, CG arm, and optional %MAC,
display a 2D diagram, and generate a PDF Weight & Balance report (with CG diagram on page 1).

> Presets are for engineering support only – always verify against your approved W&B data.
"""
)

# Sidebar: logo, link, units
with st.sidebar:
    # Logo from your website
    st.image(LOGO_URL, use_column_width=True)

    # Website link
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
    # Aircraft type pre-filled from preset but still editable
    aircraft_type = st.text_input("Aircraft type", value=preset["label"])
with dcol2:
    registration = st.text_input("Registration", value="")
    msn = st.text_input("MSN", value="")
with dcol3:
    weighing_place = st.text_input("Weighing location", value="")
    scales_cal_date = st.text_input("Scales calibration date", value="")
    weighing_date = st.text_input("Weighing date", value=datetime.now().strftime("%Y-%m-%d"))

st.markdown("---")
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
    st.markdown("### Gear Arms (from datum)")

    if preset["type"] == "dual_bogie":
        nlg_arm = st.number_input(
            f"NLG arm ({arm_unit})",
            value=preset["nlg_arm"],
            step=1.0,
            help="From WBM. Provided value: 268 in for B787."
        )
        lmlg_fwd_arm = st.number_input(
            f"LMLG FWD arm ({arm_unit})",
            value=preset["lmlg_fwd_arm"],
            step=1.0,
            help="From WBM. Provided value: 1137.30 in for B787."
        )
        lmlg_aft_arm = st.number_input(
            f"LMLG AFT arm ({arm_unit})",
            value=preset["lmlg_aft_arm"],
            step=1.0,
            help="From WBM. Provided value: 1194.80 in for B787."
        )
        rmlg_fwd_arm = st.number_input(
            f"RMLG FWD arm ({arm_unit})",
            value=preset["rmlg_fwd_arm"],
            step=1.0,
            help="Symmetric to LMLG FWD."
        )
        rmlg_aft_arm = st.number_input(
            f"RMLG AFT arm ({arm_unit})",
            value=preset["rmlg_aft_arm"],
            step=1.0,
            help="Symmetric to LMLG AFT."
        )
    else:
        nlg_arm = st.number_input(
            f"NLG arm ({arm_unit})",
            value=preset["nlg_arm"],
            step=1.0,
            help="From WBM. Example: 93 in for B737."
        )
        lmlg_arm = st.number_input(
            f"LMLG arm ({arm_unit})",
            value=preset["lmlg_arm"],
            step=1.0,
            help="From WBM. Example: 706.822 in for B737."
        )
        rmlg_arm = st.number_input(
            f"RMLG arm ({arm_unit})",
            value=preset["rmlg_arm"],
            step=1.0,
            help="From WBM. Example: 706.822 in for B737."
        )

st.markdown("---")
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

calculate = st.button("Calculate CG", type="primary")

if calculate:
    try:
        # Build weighing points list depending on aircraft layout
        if preset["type"] == "dual_bogie":
            points: List[WeighPoint] = [
                WeighPoint("NLG", nlg_w, nlg_arm),
                WeighPoint("LMLG FWD", lmlg_fwd_w, lmlg_fwd_arm),
                WeighPoint("LMLG AFT", lmlg_aft_w, lmlg_aft_arm),
                WeighPoint("RMLG FWD", rmlg_fwd_w, rmlg_fwd_arm),
                WeighPoint("RMLG AFT", rmlg_aft_w, rmlg_aft_arm),
            ]
            gear_arms = [nlg_arm, lmlg_fwd_arm, lmlg_aft_arm, rmlg_fwd_arm, rmlg_aft_arm]
            gear_labels = ["NLG", "LMLG FWD", "LMLG AFT", "RMLG FWD", "RMLG AFT"]
        else:
            points = [
                WeighPoint("NLG", nlg_w, nlg_arm),
                WeighPoint("LMLG", lmlg_w, lmlg_arm),
                WeighPoint("RMLG", rmlg_w, rmlg_arm),
            ]
            gear_arms = [nlg_arm, lmlg_arm, rmlg_arm]
            gear_labels = ["NLG", "LMLG", "RMLG"]

        result = compute_cg(points, lemac_arm=lemac_arm, mac_length=mac_length)

        res_col1, res_col2 = st.columns([1, 1.2])

        with res_col2:
            st.markdown("## Aircraft CG Diagram (Side View)")
            fig = draw_aircraft_diagram(
                gear_arms=gear_arms,
                gear_labels=gear_labels,
                cg_arm=result.cg_arm,
                lemac_arm=lemac_arm,
                mac_length=mac_length,
            )
            st.pyplot(fig)

            # Save CG diagram to PNG in memory for PDF
            cg_buffer = BytesIO()
            fig.savefig(cg_buffer, format="png", bbox_inches="tight")
            cg_buffer.seek(0)

        with res_col1:
            st.markdown("## Results")

            st.metric(
                label=f"Total weight ({weight_unit})",
                value=f"{result.total_weight:,.1f}"
            )
            st.metric(
                label=f"CG arm ({arm_unit} from datum)",
                value=f"{result.cg_arm:.2f}"
            )

            if result.mac_percent is not None:
                st.metric(
                    label="CG position (% MAC)",
                    value=f"{result.mac_percent:.2f} %"
                )
                st.caption("Check against your approved CG envelope for this aircraft type.")

            # Show a small table of moments for traceability
            st.markdown("### Moments")
            st.table({
                "Point": [p.name for p in points],
                f"Weight ({weight_unit})": [p.weight for p in points],
                f"Arm ({arm_unit})": [p.arm for p in points],
                "Moment": [p.weight * p.arm for p in points],
            })

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
                weighing_place=weighing_place,
                scales_cal_date=scales_cal_date,
                weighing_date=weighing_date,
                cg_diagram_png=cg_buffer,
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
    st.info("Select aircraft type, enter aircraft details and weighing data, then click **Calculate CG**.")
