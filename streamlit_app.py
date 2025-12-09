# ---------- Aircraft presets (update with your real WBM data) ----------

# NOTE:
# • 737 values below use your provided real example:
#   NLG arm = 93 in, MLG arm = 706.822 in (from datum).
# • 787 values are still illustrative placeholders and MUST be replaced
#   with your approved Boeing 787 WBM data before operational use.

AIRCRAFT_PRESETS = {
    "Boeing 787": {
        "label": "Boeing 787",
        # TODO: replace with real B787 arms from WBM
        "nlg_arm": 200.0,       # placeholder
        "lmlg_arm": 800.0,      # placeholder
        "rmlg_arm": 800.0,      # placeholder
        "lemac": 700.0,         # placeholder
        "mac_length": 30.0,     # placeholder
    },
    "Boeing 737": {
        "label": "Boeing 737",
        # Values below based on your example data (inches from datum)
        "nlg_arm": 93.0,        # Nose Landing Gear arm (in)
        "lmlg_arm": 706.822,    # Main Landing Gear arm (in)
        "rmlg_arm": 706.822,    # Assuming symmetric MLG
        # LEMAC / MAC here are still illustrative – replace with real 737 WBM data
        "lemac": 610.0,         # placeholder example ~ slightly ahead of CG range
        "mac_length": 130.0,    # placeholder example chord length
    },
}
