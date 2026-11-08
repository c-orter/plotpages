"""Error types and the figure / alert shown when a plot page fails."""

from __future__ import annotations

import plotly.graph_objects as go
from dash import html


class UserError(Exception):
    """Raise from `process` / `plot` for expected, user-facing problems.

    The message is shown to the user as-is (e.g. "No data for 2019") and is
    not logged as a failure. Any other exception is logged and shown as a
    generic error.
    """


def error_figure(message: str) -> go.Figure:
    """An empty figure with `message` centred on it (keeps the graph's size)."""
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, font={"size": 16}, xref="paper", yref="paper", x=0.5, y=0.5)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig


def error_alert(message: str, *, detail: str | None = None, level: str = "error") -> html.Div:
    """Alert box. `level` is "error" or "warning"; `detail` goes in a <details>."""
    children = [html.Div(message)]
    if detail:
        children.append(html.Details([html.Summary("Details"), html.Pre(detail)]))
    return html.Div(children, className=f"pp-alert pp-alert-{level}", role="alert")
