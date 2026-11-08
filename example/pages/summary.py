"""Summary: `plot` returns Dash components, not a figure, so the framework renders them instead of a graph.

No toolbar (download=()): png/html need a figure, and csv needs a DataFrame (process returns a dict here).
"""

from dash import html

from sample_data import orders
from plotpages import UserError, register_page_plot
from ui import page_header


def process(params):
    year = params["year"]
    df, prev = orders(params["region"], year), orders(params["region"], year - 1)
    if df.empty:
        raise UserError(f"No orders for {params['region']} in {year}.")

    def totals(d):
        revenue, n = d["revenue"].sum(), d["orders"].sum()
        return {"revenue": revenue, "orders": n, "aov": revenue / n if n else 0}

    return {
        "year": year,
        "now": totals(df),
        "prev": totals(prev) if not prev.empty else None,
        "top_product": df.groupby("product")["revenue"].sum().idxmax(),
        "top_channel": df.groupby("channel")["revenue"].sum().idxmax(),
    }


def card(label, value, delta=None):
    return html.Div(
        [html.Div(label, className="kpi-label"), html.Div(value, className="kpi-value"), html.Div(delta, className="kpi-delta")],
        className="kpi",
    )


def plot(data, params):
    now, prev, year = data["now"], data["prev"], data["year"]

    def delta(key):
        if not prev or not prev[key]:
            return "No prior year"
        change = now[key] / prev[key] - 1
        arrow = "▲" if change >= 0 else "▼"
        return f"{arrow} {abs(change):.1%} vs {year - 1}"

    return html.Div(
        [
            card("Revenue", f"${now['revenue']:,.0f}", delta("revenue")),
            card("Orders", f"{now['orders']:,.0f}", delta("orders")),
            card("Average order", f"${now['aov']:,.2f}", delta("aov")),
            card("Top product", data["top_product"]),
            card("Top channel", data["top_channel"]),
        ],
        className="kpis",
    )


register_page_plot(
    path="/summary",
    name="Summary",
    title="Summary",
    order=1,
    layout=lambda: page_header("Summary", "Headline numbers for the selected region and year, compared with the year before."),
    process=process,
    plot=plot,
    download=(),
)
