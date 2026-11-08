"""Cohort retention: a sequential heatmap and a URL-only param.

`months` has no control. It exists only as `?months=6` (e.g. from a link in a report), via a store.
"""

import plotly.graph_objects as go
from dash import dcc

from sample_data import cohorts
from plotpages import Param, register_page_plot
from ui import page_header


def process(params):
    return cohorts(params["region"], params["year"])[["cohort", *range(params["months"] + 1)]]


def plot(df, params):
    retention = df.drop(columns="cohort")
    fig = go.Figure(
        go.Heatmap(
            z=retention.values,
            x=[f"Month {k}" for k in retention.columns],
            y=df["cohort"],
            zmin=0,
            zmax=1,
            xgap=2,
            ygap=2,
            hoverongaps=False,
            texttemplate="%{z:.0%}",
            colorbar={"tickformat": ".0%", "thickness": 12, "outlinewidth": 0},
            hovertemplate="%{y}, month %{x}<br>%{z:.1%} still active<extra></extra>",
        )
    )
    fig.update_layout(hovermode="closest")
    fig.update_xaxes(showgrid=False, side="top")
    fig.update_yaxes(showgrid=False, autorange="reversed")
    return fig


register_page_plot(
    path="/cohorts",
    name="Retention",
    title="Retention",
    order=3,
    layout=lambda: page_header("Retention", "Share of each monthly signup cohort still active. Add ?months=6 to the URL for a shorter view."),
    process=process,
    plot=plot,
    params=[Param("months", dcc.Store(id="_", data=12), prop="data")],
    download=("png", "csv"),
    height="30rem",
)
