from plotly import colors

DEFAULT_DISCRETE_COLORS = [
    f"hsl{c}"
    # for c in colors.n_colors((210, 100, 35), (200, 147, 85), 20, colortype="hsl") # Blue
    for c in colors.n_colors((30, 93, 60), (60, 60, 90), 20, colortype="hsl")  # Gold
]

DEFAULT_LAYOUT = {
    "font": {
        "family": "Courier New, mono",
        "size": 16,
    },
    "title_font": {
        "family": "Courier New, mono",
        "size": 32,
    },
    "margin": {
        "pad": 10,
    },
    "height": None,
    "width": None,
}
