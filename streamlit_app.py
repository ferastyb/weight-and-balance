import streamlit as st
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Optional, List
from io import BytesIO
from datetime import datetime

# ---------- Logo & Website Header ----------

LOGO_URL = "https://www.ferasaviation.info/gallery/FA__logo.png?ts=1754692591"
WEBSITE_URL = "https://www.ferasaviation.info"


# ---------- Core data structures & logic ----------

@dataclass
class WeighPoint:
    name: str       # e.g. "NLG", "LMLG", "RMLG"
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


def draw_aircraft_diagram(nlg_arm: float,
                          lmlg_arm: float,
                          rmlg_arm: float,
                          cg_arm: float,
                          lemac_arm: Optional[float] = None,
                          mac_length: Optional[float] = None):
    """
    Draw a simple 2D side-view diagram of the aircraft with:
    - Fuselage as a bar
    - Gear positions
    - MAC span (if given)
    - CG location
    Arms are scaled linearly between min and max arms.
    """

    arms = [nlg_arm, lmlg_arm, rmlg_arm, cg_arm]
    if lemac_arm is not None and mac_length is not None:
        arms.extend([lemac_arm, lemac_arm + mac_length])

    min_arm = min(arms)
    max_arm = max(arms)

    # Normalised positions (0–1 along fuselage bar)
    x_nlg = normalise(nlg_arm, min_arm, max_arm)
    x_lmlg = normalise(lmlg_arm, min_arm, max_arm)
    x_rmlg = normalise(rmlg_arm, min_arm, max_arm)
    x_cg = normalise(cg_arm, min_arm, max_arm)

    if lemac_arm is not None and mac_length is not None:
        x_lemac = normalise(lemac_arm, min_arm, max_arm)
        x_tlemac = normalise(lemac_arm + mac_length, min_arm, max_arm)
    else:
        x_lemac = x_tlemac = None

    fig, ax = plt.subplots(figsize=(8, 2))

    # Fuselage bar
    ax.hlines(0.5, 0.02, 0.98, linewidth=6)

    # Nose & tail markers
    ax.text(0.02, 0.6, "Nose", ha="left", va="bottom", fontsize=8)
    ax.text(0.98, 0.6, "Tail", ha="right", va="bottom", fontsize=8)

    # Gear markers
    gear_y = 0.35
    ax.vlines(x_nlg, 0.5, gear_y, linewidth=3)
    ax.scatter([x_nlg], [gear_y], s=60)
    ax.text(x_nlg, gear_y - 0.08, "NLG", ha="center", va="top", fontsize=8)

    ax.vlines(x_lmlg, 0.5, gear_y, linewidth=3)
    ax.scatter([x_lmlg], [gear_y], s=60)
    ax.text(x_lmlg, gear_y - 0.08, "LMLG", ha="center", va="top", fontsize=8)

    ax.vlines(x_rmlg, 0.5, gear_y, linewidth=3)
    ax.scatter([x_rmlg], [gear_y], s=60)
    ax.text(x_rmlg, gear_y - 0.18, "RMLG", ha="center", va="top", fontsize=8)

    # MAC region (if available)
    if x_lemac is not None and x_tlemac is not None:
        mac_y = 0.62
        ax.hlines(mac_y, x_lemac, x_tlemac, linewidth=4)
        ax.vlines(x_lemac, mac_y - 0.02, mac_y + 0.02, linewidth=2)
        ax.vlines(x_tlemac, mac_y - 0.02, mac_y + 0.02, linewidth=2)
        ax.text(x_lemac, mac_y + 0.03, "LEMAC", ha="center", va="bottom", fontsize=8)
        ax.text(x_tlemac, mac_y + 0.03, "TEMAC", ha="center", va="bottom", fontsize=8)
        ax.text((x_lemac + x_tlemac) / 2, mac_y + 0.05, "MAC",
                ha="center", va="bottom", fontsize=8)

    # CG marker
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
    lemac_arm: Optional[float] = None,
    mac_length: Optional[float] = None,
) -> BytesIO:
    """
    Build a simple one-page PDF weight & balance report and return it as an in-memory buffer.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    margin_x = 40
    y = height - 50

    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin_x, y, "Boeing 787 Weight & Balance Report")
    y -= 25

    # Date/time
    c.setFont("Helvetica", 10)
    c.drawString(margin_x, y, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 15
    c.drawString(margin_x, y, f"Website: {WEBSITE_URL}")
    y -= 25

    # Summary
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin_x, y, "Summary")
    y -= 18

    c.setFont("Helvetica", 11)
    c.drawString(margin_x, y, f"Total weight: {result.total_weight:,.1f} {weight_unit}")
    y -= 15
    c.drawString(margin_x, y, f"CG arm: {result.cg_arm:.2f} {arm_unit} from datum")
    y -= 15

    if result.mac_percent is not None and lemac_arm is not None and mac_length is not None:
        c.drawString(margin_x, y, f"CG position: {result.mac_percent:.2f} % MAC")
        y -= 15
        c.drawString(margin_x, y, f"LEMAC: {lemac_arm:.2f} {arm_unit}   MAC length: {mac_length:.2f} {arm_unit}")
        y -= 20
    else:
        y -= 10

    # Table header
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin_x, y, "Gear Weighing Data")
    y -= 18

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
        if y < 60:  # basic page break
            c.showPage()
            y = height - 50

    y -= 20
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(
        margin_x,
        y,
        "Note: This report is generated by Feras Aviation B787 CG Calculator tool. "
        "Verify against approved W&B data and procedures."
    )

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


# ---------- Streamlit UI ----------

st.set_page_config(
    page_title="B787 CG Calculator",
    layout="wide",
)

st.title("Boeing 787 Weighing – Centre of Gravity Calculator")

st.markdown(
    """
Enter your **scale readings** and **arms from datum**.  
The app will compute total weight, CG arm, and optional %MAC,
and display a simple 2D aircraft diagram with CG.
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
        • Use arms from the *same datum*  
        • Use official B787 WBM data for arms, LEMAC & MAC  
        """
    )

st.subheader("Weighing Inputs")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Gear Weights")
    nlg_w = st.number_input(f"NLG weight ({weight_unit})", min_value=0.0, value=30000.0, step=100.0)
    lmlg_w = st.number_input(f"LMLG weight ({weight_unit})", min_value=0.0, value=80000.0, step=100.0)
    rmlg_w = st.number_input(f"RMLG weight ({weight_unit})", min_value=0.0, value=80000.0, step=100.0)

with col2:
    st.markdown("### Gear Arms (from datum)")
    nlg_arm = st.number_input(f"NLG arm ({arm_unit})", value=200.0, step=1.0)
    lmlg_arm = st.number_input(f"LMLG arm ({arm_unit})", value=800.0, step=1.0)
    rmlg_arm = st.number_input(f"RMLG arm ({arm_unit})", value=800.0, step=1.0)

st.markdown("---")
st.subheader("MAC / CG Envelope Reference (optional)")

col3, col4 = st.columns(2)
with col3:
    lemac_arm = st.number_input(
        f"LEMAC arm ({arm_unit})",
        value=700.0,
        step=1.0,
        help="Leading edge of MAC from same datum. Replace with real 787 data."
    )
with col4:
    mac_length = st.number_input(
        f"MAC length ({arm_unit})",
        value=30.0,
        step=0.1,
        help="Mean aerodynamic chord length. Needed for %MAC."
    )

calculate = st.button("Calculate CG", type="primary")

if calculate:
    try:
        points = [
            WeighPoint("NLG", nlg_w, nlg_arm),
            WeighPoint("LMLG", lmlg_w, lmlg_arm),
            WeighPoint("RMLG", rmlg_w, rmlg_arm),
        ]

        result = compute_cg(points, lemac_arm=lemac_arm, mac_length=mac_length)

        res_col1, res_col2 = st.columns([1, 1.2])

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
                st.caption("Check against your approved B787 CG envelope.")

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
            )

            st.download_button(
                label="📄 Download PDF Weight & Balance Report",
                data=pdf_buffer,
                file_name=f"b787_wb_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf",
            )

        with res_col2:
            st.markdown("## Aircraft CG Diagram (Side View)")
            fig = draw_aircraft_diagram(
                nlg_arm=nlg_arm,
                lmlg_arm=lmlg_arm,
                rmlg_arm=rmlg_arm,
                cg_arm=result.cg_arm,
                lemac_arm=lemac_arm,
                mac_length=mac_length,
            )
            st.pyplot(fig)

    except Exception as e:
        st.error(f"Error during calculation: {e}")
else:
    st.info("Enter your weighing data and click **Calculate CG**.")
