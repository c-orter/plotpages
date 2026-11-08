"""`register_page_plot`: register a multipage-Dash page from layout / process / plot functions."""

from __future__ import annotations

import copy
import inspect
import json
import logging
import re
import traceback
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import dash
import flask
import plotly.graph_objects as go
from dash import Input, Output, State, callback, clientside_callback, dcc, html
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate

from . import theme as _theme
from .errors import UserError, error_alert, error_figure

log = logging.getLogger(__name__)
_PRESETS: list[Param] = []


@dataclass
class Param:
    """A user-controlled input to the plot.

    `Param("region", dcc.Dropdown(...), label="Region")` renders the component
    (the framework assigns its id). To bind a component your `layout` function
    already renders, use `Param("region", id="my-dropdown")` (and `prop=` if it
    isn't `value`). For a URL-only param (no control), pass a store:
    `Param("n", dcc.Store(id="_", data=150), prop="data")`; stores render nothing.
    The plot functions receive `{name: value}`.
    """

    name: str
    component: Component | None = None
    label: str | None = None
    id: str | None = None
    prop: str = "value"


def configure(*, presets: Sequence[Param]) -> None:
    """Declare the app-wide preset params (e.g. `a`, `b`) every page gets by default.

    Call once, before any page is registered (i.e. before `Dash(use_pages=True)`).
    """
    _PRESETS[:] = presets


def register_page_plot(
    *,
    path: str,
    process: Callable[..., Any],
    plot: Callable[..., Any],
    layout: Callable[..., Component] | None = None,
    params: Sequence[Param] = (),
    presets: bool | Sequence[str] = True,
    name: str | None = None,
    title: str | Callable[..., str] | None = None,
    order: int | None = None,
    errors: bool = True,
    loading: bool = True,
    theme: bool = True,
    url: bool = True,
    download: Sequence[str] = ("png", "html"),
    cache: int = 0,
    height: str = "70vh",
    **page_kwargs: Any,
) -> Callable[[], Component]:
    """Register a page at `path` and return its layout function.

    Core pieces (each may take fewer arguments than shown):
      process(params: dict) -> data          load / transform
      plot(data, params: dict) -> Figure     draw; return a Dash component instead (cards, tables,
                                             ...) to render it in place of the graph. Themeing is
                                             then yours, and "png"/"html" downloads don't apply.
      layout() -> Component                  optional static content (title, text)

    Opt-out switches:
      params    Param list -> controls rendered above the plot and passed in `params`.
      presets   app-wide Params from `configure(presets=...)`: True (all), False, or names.
                They come first in `params`.
      url       mirror every Param with a component in the URL's search string, and
                restore them from it on load (the theme is not in the URL; it lives in
                localStorage). A Param's type comes from its
                component's default value (list -> JSON, int, float, bool, str), so give
                components a default. Params bound only by `id=` are not mirrored.
      errors    catch exceptions: log, show an alert + placeholder figure. `UserError`
                messages are shown verbatim; others show a generic message (traceback
                in debug mode).
      loading   wrap the graph / custom content in `dcc.Loading`.
      theme     follow the app-wide light/dark switch (needs `theme_provider()`).
      download  any of "png" (client-side), "html", "csv" (data must have `.to_csv`).
                Empty tuple for no toolbar.
      cache     keep the last N `process` results keyed by params (0 = off). Results
                are shared between users and must not be mutated by `plot`.
    `title` may be a string or a callable returning one (Dash calls it with the URL's query params).
    Extra keyword arguments go to `dash.register_page`.
    """
    key = re.sub(r"\W+", "-", path.strip("/")).strip("-") or "home"
    wanted = [p.name for p in _PRESETS] if presets is True else presets or ()
    # copies, so pages never share (or mutate) the configured components
    params = [copy.deepcopy(p) for p in _PRESETS if p.name in wanted] + list(params)
    names = [p.name for p in params]
    for p in params:
        p.id = p.id or f"{key}-param-{p.name}"
        if p.component is not None:
            p.component.id = p.id
    shown = [p for p in params if p.component is not None]

    graph_id, content_id, error_id = f"{key}-graph", f"{key}-content", f"{key}-error"
    sink_id, url_sink_id = f"{key}-sink", f"{key}-urlsink"
    get_data = _memoize(lambda p: _call(process, p), cache)

    # ---- layout ----------------------------------------------------------
    def control(p: Param, query: dict) -> Component:
        comp = p.component
        if url and p.name in query:  # initial value from the URL (copy: the original is shared)
            comp = copy.deepcopy(comp)
            setattr(comp, p.prop, _decode(query[p.name], getattr(comp, p.prop, None)))
        if isinstance(comp, dcc.Store):  # URL-only param: nothing to show
            return comp
        return html.Div([html.Label(p.label or p.name, htmlFor=p.id), comp], className="pp-param")

    def page_layout(**query: Any) -> Component:  # Dash passes the URL's query params as kwargs
        parts: list[Any] = []
        if layout is not None:
            try:
                parts.append(_call(layout))
            except Exception as e:
                if not errors:
                    raise
                log.exception("layout for plot page %r failed", key)
                parts.append(_unexpected(e))
        if shown:
            parts.append(html.Div([control(p, query) for p in shown], className="pp-controls"))
        if download:
            parts.append(
                html.Div(
                    [
                        html.Button(k.upper(), id=f"{key}-dl-{k}", n_clicks=0, title=f"Download as {k.upper()}")
                        for k in download
                    ],
                    className="pp-toolbar",
                )
            )
        if errors:
            parts.append(html.Div(id=error_id))
        # Whether plot() returns a figure or a component is only known per call, so both slots exist.
        body = [
            dcc.Graph(id=graph_id, style={"height": height}, config={"displaylogo": False}),
            html.Div(id=content_id),
        ]
        parts += [dcc.Loading(body, type="default")] if loading else body
        parts += [dcc.Store(id=sink_id), dcc.Store(id=url_sink_id)] + [
            dcc.Download(id=f"{key}-file-{k}") for k in ("html", "csv") if k in download
        ]
        return html.Div(parts, className="pp-page")

    # ---- main callback ---------------------------------------------------
    inputs = [Input(p.id, p.prop) for p in params] + ([Input(_theme.STORE_ID, "data")] if theme else [])
    outputs = [Output(graph_id, "figure"), Output(graph_id, "style"), Output(content_id, "children")]
    outputs += [Output(error_id, "children")] if errors else []

    @callback(*outputs, *inputs)
    def update(*values):
        params_ = dict(zip(names, values))
        content = alert = None
        try:
            result = _call(plot, get_data(params_), params_)
            if isinstance(result, Component):
                content = result
            else:
                fig = go.Figure(result)
        except Exception as e:
            if not errors or isinstance(e, PreventUpdate):
                raise
            if isinstance(e, UserError):
                fig, alert = error_figure(str(e)), error_alert(str(e), level="warning")
            else:
                log.exception("plot page %r failed", key)
                fig, alert = error_figure("Could not draw this plot"), _unexpected(e)
        if content is not None:  # custom UI: hide the graph, show the component
            out = (dash.no_update, {"display": "none"}, content)
        else:
            if theme:
                fig.update_layout(template=_theme.TEMPLATES["dark" if values[-1] == "dark" else "light"])
            out = (fig, {"height": height}, None)
        return (*out, alert) if errors else out

    # ---- URL mirror (replaceState: no navigation, no page re-render) ------
    if url and shown:
        clientside_callback(
            """function(){
                var names = %s, q = new URLSearchParams();
                for (var i = 0; i < names.length; i++) {
                    var v = arguments[i];
                    q.set(names[i], v === null || v === undefined ? '' : (typeof v === 'object' ? JSON.stringify(v) : String(v)));
                }
                history.replaceState(history.state, '', location.pathname + '?' + q.toString() + location.hash);
                return window.dash_clientside.no_update;
            }"""
            % json.dumps([p.name for p in shown]),
            Output(url_sink_id, "data"),
            *[Input(p.id, p.prop) for p in shown],
        )

    # ---- downloads -------------------------------------------------------
    if "png" in download:
        clientside_callback(
            """function(n){
                if (n) {
                    var gd = document.querySelector('#' + %s + ' .js-plotly-plot');
                    if (gd) window.Plotly.downloadImage(gd, {format: 'png', filename: %s});
                }
                return window.dash_clientside.no_update;
            }"""
            % (json.dumps(graph_id), json.dumps(key)),
            Output(sink_id, "data"),
            Input(f"{key}-dl-png", "n_clicks"),
            prevent_initial_call=True,
        )
    if "html" in download:

        @callback(
            Output(f"{key}-file-html", "data"),
            Input(f"{key}-dl-html", "n_clicks"),
            State(graph_id, "figure"),
            prevent_initial_call=True,
        )
        def download_html(n, figure):
            return dcc.send_string(go.Figure(figure).to_html(include_plotlyjs=True), f"{key}.html")

    if "csv" in download:

        @callback(
            Output(f"{key}-file-csv", "data"),
            Input(f"{key}-dl-csv", "n_clicks"),
            [State(p.id, p.prop) for p in params],
            prevent_initial_call=True,
        )
        def download_csv(n, *values):
            return dcc.send_string(get_data(dict(zip(names, values))).to_csv(index=False), f"{key}.csv")

    dash.register_page(f"pp.{key}", path=path, name=name, title=title, order=order, layout=page_layout, **page_kwargs)
    return page_layout


# ---- helpers ------------------------------------------------------------
def _call(fn: Callable, *args: Any) -> Any:
    """Call `fn` with as many of `args` as it accepts, so `plot(data)` works too."""
    ps = inspect.signature(fn).parameters.values()
    if any(p.kind is p.VAR_POSITIONAL for p in ps):
        return fn(*args)
    return fn(*args[: sum(p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD) for p in ps)])


def _decode(raw: Any, default: Any) -> Any:
    """URL string (or list, for repeated keys) -> value of the same type as `default`."""
    if isinstance(raw, list):  # repeated key: ?regions=a&regions=b
        raw = json.dumps(raw)
    if isinstance(default, str):  # keep strings verbatim: "2024" must not become 2024
        return raw
    try:
        value = json.loads(raw)
    except ValueError:
        value = raw if raw else None  # bare word (?regions=north) or cleared input
    if isinstance(default, list) and not isinstance(value, list):
        return [value]
    if isinstance(default, (int, float)) and value is not None and not isinstance(value, (int, float)):
        return default  # ?b=oops
    return value


def _memoize(fn: Callable[[dict], Any], size: int) -> Callable[[dict], Any]:
    if not size:
        return fn
    cached = lru_cache(maxsize=size)(lambda k: fn(json.loads(k)))
    return lambda p: cached(json.dumps(p, sort_keys=True, default=str))


def _unexpected(e: Exception) -> html.Div:
    debug = flask.has_app_context() and flask.current_app.debug
    detail = traceback.format_exc() if debug else type(e).__name__
    return error_alert("Something went wrong while building this plot.", detail=detail)
