# B787 Centre of Gravity Calculator (Streamlit)

A small Streamlit application to calculate the **Boeing 787** centre of gravity
after weighing, using scale readings at each landing gear leg.

It also displays a simple 2D side-view diagram of the aircraft showing:

- Nose landing gear (NLG) position  
- Left & right main landing gear (LMLG / RMLG)  
- Mean Aerodynamic Chord (MAC) span  
- Computed CG position  

> ⚠️ **Safety note:**  
> This tool is for engineering support and training.  
> For operational or certification use, always follow your approved Boeing /
> airline Weight & Balance Manual and internal procedures.

---

## Features

- Input:
  - NLG, LMLG, RMLG scale readings
  - Arm of each gear relative to a chosen datum
  - LEMAC arm and MAC length (for %MAC)
- Output:
  - Total weight
  - CG arm (from datum)
  - CG as `% MAC`
  - Tabulated weights, arms, and moments
  - Simple side-view diagram with CG marker

---

## How to run locally

1. **Clone the repository**

   ```bash
   git clone https://github.com/<your-username>/b787-cg-calculator.git
   cd b787-cg-calculator
   ```

2. **Create virtual environment (optional but recommended)**

   ```bash
   python -m venv .venv
   source .venv/bin/activate        # on macOS / Linux
   # .venv\Scripts\activate         # on Windows
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app**

   ```bash
   streamlit run streamlit_app.py
   ```

5. Open the URL shown in the terminal (usually http://localhost:8501).

---

## Usage

1. Enter NLG, LMLG, and RMLG **weights** (kg or lb).  
2. Enter the corresponding **arms** from the aircraft datum, using the same unit
   (inches or metres).  
3. Optionally enter:
   - **LEMAC arm**
   - **MAC length**

   from your approved B787 Weight & Balance Manual.

4. Click **"Calculate CG"**.

You will see:

- Total weight  
- CG position from datum  
- CG as `% MAC`  
- A small table showing moments  
- A side-view diagram with CG and MAC displayed  

---

## Deployment (Streamlit Cloud)

1. Push this repository to GitHub.
2. Go to Streamlit Cloud.
3. Create a new app:
   - **Repository**: `your-username/b787-cg-calculator`
   - **Branch**: `main` (or `master`)
   - **Main file**: `streamlit_app.py`
4. Deploy.

Streamlit Cloud will read `requirements.txt` and install the dependencies.

---

## Customisation

- Replace dummy arms and weights with your **real Boeing 787** data.
- You can later integrate a **real 2D diagram image** and overlay the CG position.

---

## Disclaimer

This tool does not replace any regulatory- or manufacturer-approved
Weight & Balance computation methods. Always verify results against official
documentation and approved software.
