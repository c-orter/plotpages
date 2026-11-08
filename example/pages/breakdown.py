"""Breakdown: a slider, a text filter, and `UserError` for an expected empty result."""

import plotly.graph_objects as go
from dash import dcc

from sample_data import orders
from plotpages import Param, UserError, register_page_plot
from ui import page_header


def process(params):
    df = orders(params["region"], params["year"])
    search, by = params["search"], params["by"]
    if search:
        df = df[df["product"].str.contains(search, case=False, regex=False)]
        if df.empty:
            raise UserError(f"No products match “{search}”.")
    return df.groupby(by)["revenue"].sum().nlargest(params["top_n"]).reset_index()


def plot(df, params):
    by = params["by"]
    fig = go.Figure(
        go.Bar(
            x=df["revenue"],
            y=df[by],
            orientation="h",
            texttemplate="$%{x:.3~s}",
            textposition="outside",
            cliponaxis=False,
            hovertemplate="$%{x:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(hovermode="closest", bargap=0.45)
    fig.update_xaxes(showgrid=True, tickprefix="$", tickformat="~s")
    fig.update_yaxes(showgrid=False, autorange="reversed")
    return fig


register_page_plot(
    path="/breakdown",
    name="Breakdown",
    title="Breakdown",
    order=2,
    layout=lambda: page_header("Breakdown", "Where revenue comes from. Try searching for a product that does not exist."),
    process=process,
    plot=plot,
    params=[
        Param(
            "by",
            dcc.Dropdown(options=["product", "category", "channel"], value="product", clearable=False),
            label="Group by",
        ),
        Param(
            "top_n",
            dcc.Slider(min=3, max=12, step=1, value=8, marks={3: "3", 6: "6", 9: "9", 12: "12"}),
            label="Show top",
        ),
        Param("search", dcc.Input(type="text", value="", placeholder="Filter products…", debounce=True), label="Search"),
    ],
    download=("png", "csv"),
    cache=8,
    height="26rem",
)
