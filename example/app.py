"""Meridian Analytics: a sample app built on plotpages.

Run:  python example/app.py   (pip install -e ".[dev]" first)
"""

import dash
from dash import Dash, Input, Output, clientside_callback, dcc, html

import chart_theme
from sample_data import REGIONS, YEARS
from plotpages import Param, configure, theme_provider

# App-wide filters: every page gets these first (opt out per page with presets=False / a list of names).
# Must run before Dash(use_pages=True) imports the pages.
configure(
    presets=[
        Param("region", dcc.Dropdown(options=["All", *REGIONS], value="All", clearable=False), label="Region"),
        Param("year", dcc.Dropdown(options=YEARS, value=2024, clearable=False), label="Year"),
    ]
)
chart_theme.install()

app = Dash(__name__, use_pages=True, title="Meridian Analytics")

pages = sorted(dash.page_registry.values(), key=lambda p: p["order"])
app.layout = html.Div(
    [
        dcc.Location(id="app-url", refresh=False),
        dcc.Store(id="nav-sink"),
        html.Aside(
            [
                html.Div("Meridian", className="brand"),
                html.Nav([dcc.Link(p["name"], href=p["relative_path"], className="nav-link") for p in pages], className="nav"),
            ],
            className="sidebar",
        ),
        html.Div(
            [
                html.Header([html.Span("Analytics", className="crumb"), theme_provider()], className="topbar"),
                html.Main(dash.page_container, className="content"),
            ],
            className="main",
        ),
    ],
    className="app",
)

# Mark the current page's link (dcc.Link has no active state of its own).
clientside_callback(
    """function(path){
        document.querySelectorAll('.nav-link').forEach(function(a){
            a.toggleAttribute('data-active', a.getAttribute('href') === path);
        });
        return window.dash_clientside.no_update;
    }""",
    Output("nav-sink", "data"),
    Input("app-url", "pathname"),
)

if __name__ == "__main__":
    app.run(debug=True)
