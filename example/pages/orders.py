"""Order values: a list-valued param (JSON in the URL) and a control bound by id from the layout."""

import plotly.graph_objects as go
from dash import dcc, html

from chart_theme import entity_traces
from sample_data import CHANNELS, order_values
from plotpages import Param, UserError, register_page_plot
from ui import page_header


def layout():
    # A component the page renders itself; `Param("log", id="orders-log")` below binds to it.
    # (Bound-by-id params are not mirrored in the URL; the framework doesn't render them.)
    return html.Div(
        [
            page_header("Order values", "Spread of individual order values per channel."),
            dcc.Checklist(id="orders-log", options=[{"label": "Log scale", "value": "log"}], value=[], className="option"),
        ]
    )


def process(params):
    if not params["channels"]:
        raise UserError("Select at least one channel.")
    return order_values(params["region"], params["year"], params["channels"])


def plot(df, params):
    fig = entity_traces(
        df,
        "channel",
        CHANNELS,
        lambda rows, channel: go.Box(y=rows["value"], name=channel, boxpoints=False, hovertemplate="$%{y:,.0f}"),
    )
    fig.update_layout(hovermode="closest", showlegend=False)
    return fig.update_yaxes(type="log" if "log" in params["log"] else "linear", tickprefix="$")


register_page_plot(
    path="/orders",
    name="Order values",
    title="Order values",
    order=4,
    layout=layout,
    process=process,
    plot=plot,
    params=[
        Param(
            "channels",
            dcc.Dropdown(options=CHANNELS, value=list(CHANNELS), multi=True, clearable=False),
            label="Channels",
        ),
        Param("log", id="orders-log"),
    ],
    height="28rem",
)
