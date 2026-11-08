"""Service latency: opt-outs (no presets, png only) and a failing data source for the error path."""

import plotly.graph_objects as go
from dash import dcc, html

from sample_data import latency
from plotpages import Param, register_page_plot
from ui import page_header


def layout():
    return html.Div(
        [
            page_header("Service latency", "Request latency percentiles. Pick the legacy cluster to see an unexpected failure."),
        ]
    )


def plot(df, params):
    fig = go.Figure([go.Scatter(x=df["time"], y=df[p], name=p, hovertemplate="%{y:.0f} ms") for p in ("p50", "p95", "p99")])
    return fig.update_yaxes(ticksuffix=" ms", rangemode="tozero")


register_page_plot(
    path="/services",
    name="Services",
    title="Services",
    order=5,
    layout=layout,
    process=lambda params: latency(params["env"], params["window"]),
    plot=plot,
    params=[
        Param(
            "env",
            dcc.Dropdown(
                options=[
                    {"label": "Production", "value": "production"},
                    {"label": "Staging", "value": "staging"},
                    {"label": "Legacy cluster (offline)", "value": "legacy"},
                ],
                value="production",
                clearable=False,
            ),
            label="Environment",
        ),
        Param(
            "window",
            dcc.RadioItems(
                options=[{"label": f"{h}h", "value": h} for h in (6, 24, 72)], value=24, className="segmented"
            ),
            label="Window",
        ),
    ],
    presets=False,
    download=("png",),
    height="26rem",
)
