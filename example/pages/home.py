"""Overview: every default on, plus csv download and a process cache.

Presets (region, year) come from app.py; granularity and metric are this page's own params.
"""

import plotly.graph_objects as go
from dash import dcc

from chart_theme import entity_traces
from sample_data import REGIONS, orders
from plotpages import Param, UserError, register_page_plot
from ui import page_header

RULE = {"D": "D", "W": "W", "M": "MS"}


def process(params):
    df = orders(params["region"], params["year"])
    if df.empty:
        raise UserError(f"No orders for {params['region']} in {params['year']}.")
    metric = params["metric"]
    daily = df.set_index("date").groupby("region")[metric].resample(RULE[params["granularity"]]).sum()
    return daily.rename(metric).reset_index()


def plot(df, params):
    metric = params["metric"]
    money = metric == "revenue"
    fig = entity_traces(
        df,
        "region",
        REGIONS,
        lambda rows, region: go.Scatter(
            x=rows["date"], y=rows[metric], name=region, hovertemplate="$%{y:,.0f}" if money else "%{y:,.0f}"
        ),
    )
    return fig.update_yaxes(tickprefix="$" if money else "", tickformat="~s")


register_page_plot(
    path="/",
    name="Overview",
    title="Overview",
    order=0,
    layout=lambda: page_header("Overview", "Revenue and order volume over time, by region."),
    process=process,
    plot=plot,
    params=[
        Param(
            "granularity",
            dcc.Dropdown(
                options=[{"label": "Daily", "value": "D"}, {"label": "Weekly", "value": "W"}, {"label": "Monthly", "value": "M"}],
                value="W",
                clearable=False,
            ),
            label="Granularity",
        ),
        Param(
            "metric",
            dcc.RadioItems(
                options=[{"label": "Revenue", "value": "revenue"}, {"label": "Orders", "value": "orders"}],
                value="revenue",
                className="segmented",
            ),
            label="Metric",
        ),
    ],
    download=("png", "html", "csv"),
    cache=16,
    height="28rem",
)
