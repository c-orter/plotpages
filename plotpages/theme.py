"""Light / dark mode: one app-wide switch, picked up by every plot page.

Put `theme_provider()` once in `app.layout`. It owns a `dcc.Store` (persisted
in localStorage, defaulting to the OS preference) and sets `data-theme="light|dark"`
on <html>. Plot pages read the store to choose a plotly template.

No CSS ships with this: style the page with `:root[data-theme=dark] {...}`.
"""

from __future__ import annotations

from dash import Input, Output, State, clientside_callback, dcc, html

STORE_ID = "pp-theme"
TOGGLE_ID = "pp-theme-toggle"

#: plotly templates per mode; replace entries to use your own.
TEMPLATES = {"light": "plotly_white", "dark": "plotly_dark"}


def theme_provider() -> html.Div:
    """Add once to `app.layout` (at import time, not inside a layout function)."""
    # Flip on click; on first load, use the stored value or the OS preference.
    clientside_callback(
        """function(n, cur){
            var t = cur || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
            return n ? (t === 'dark' ? 'light' : 'dark') : t;
        }""",
        Output(STORE_ID, "data"),
        Input(TOGGLE_ID, "n_clicks"),
        State(STORE_ID, "data"),
    )
    # Apply to the page: <html data-theme> and the button icon.
    clientside_callback(
        """function(t){
            document.documentElement.setAttribute('data-theme', t || 'light');
            return t === 'dark' ? '\\u2600' : '\\u263E';
        }""",
        Output(TOGGLE_ID, "children"),
        Input(STORE_ID, "data"),
    )
    return html.Div(
        [
            dcc.Store(id=STORE_ID, storage_type="local"),
            html.Button("☾", id=TOGGLE_ID, title="Toggle light / dark mode", n_clicks=0),
        ],
        className="pp-theme",
    )
