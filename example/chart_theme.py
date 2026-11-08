"""Plotly look for the example app.

The framework applies a plotly template per light/dark mode (`theme.TEMPLATES`), so pages never mention
colours: they build figures and the template supplies the categorical colorway (same hues, separate
light and dark steps), the sequential ramp, surfaces, grid and type. `install()` registers the templates.
"""

import copy

import plotly.graph_objects as go
import plotly.io as pio

from plotpages import theme

# Categorical slots 1-8, stepped separately for each surface. Pages here use at most the first three.
CATEGORICAL = {
    "light": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"],
    "dark": ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"],
}
# One-hue magnitude ramp (blue 100..700). Low values recede toward the surface, so it flips in dark mode.
BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
SURFACE = {"light": "#ffffff", "dark": "#09090b"}  # matches --card in assets/style.css
INK = {  # text, muted text, grid
    "light": ("#09090b", "#71717a", "#e4e4e7"),
    "dark": ("#fafafa", "#a1a1aa", "#27272a"),
}


def _template(mode: str, base: str) -> go.layout.Template:
    text, muted, grid = INK[mode]
    axis = {"linecolor": grid, "tickcolor": grid, "zeroline": False, "automargin": True, "title": {"standoff": 12}}
    tpl = copy.deepcopy(pio.templates[base])
    tpl.layout.update(
        colorway=CATEGORICAL[mode],
        colorscale={"sequential": BLUE if mode == "light" else BLUE[::-1]},
        font={"family": "Inter, ui-sans-serif, system-ui, sans-serif", "size": 13, "color": muted},
        paper_bgcolor=SURFACE[mode],
        plot_bgcolor=SURFACE[mode],
        margin={"l": 16, "r": 16, "t": 16, "b": 16},
        hovermode="x unified",
        hoverlabel={"bgcolor": SURFACE[mode], "bordercolor": grid, "font": {"color": text}},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0, "title": {"text": ""}},
        modebar={"bgcolor": "rgba(0,0,0,0)", "color": muted, "activecolor": text},
        xaxis={**axis, "showgrid": False, "ticks": "outside"},
        yaxis={**axis, "showgrid": True, "gridcolor": grid, "showline": False},
    )
    tpl.data.scatter = [go.Scatter(line={"width": 2})]
    return tpl


def install() -> None:
    """Register the templates and point the framework's light/dark switch at them."""
    pio.templates["meridian_light"] = _template("light", "plotly_white")
    pio.templates["meridian_dark"] = _template("dark", "plotly_dark")
    theme.TEMPLATES.update(light="meridian_light", dark="meridian_dark")


def entity_traces(df, by, order, make):
    """One trace per entity, always in `order` (absent ones empty), so a colour follows its entity.

    Without this, filtering to one region would repaint it as series 1.
    `make(rows, name)` returns the trace; absent entities are kept out of the legend.
    """
    fig = go.Figure()
    for name in order:
        rows = df[df[by] == name]
        trace = make(rows, name)
        trace.showlegend = not rows.empty
        fig.add_trace(trace)
    return fig
