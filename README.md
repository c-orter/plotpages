# plotpages

Register a Dash multipage plot page from three functions. Everything else is a switch.
Supports exactly Python 3.11, Dash 2.13.0 and Plotly 5.9.0 (pinned in `pyproject.toml`); nothing is written for other versions.

```python
# pages/sales.py
from plotpages import Param, UserError, register_page_plot

def process(params):            # load / transform -> any data
    ...
def plot(data, params):         # -> plotly Figure
    ...

register_page_plot(
    path="/sales", name="Sales", process=process, plot=plot,
    layout=lambda: html.H2("Sales"),                       # optional static content
    params=[Param("region", dcc.Dropdown(...), label="Region")],  # optional controls
)
```

App shell (once): `app.layout = html.Div([theme_provider(), dash.page_container])`

| switch | default | what it does |
|---|---|---|
| `errors` | `True` | catches exceptions from layout/process/plot; alert + placeholder figure. `raise UserError("msg")` for expected problems (shown verbatim). Others: generic message, traceback only in debug. |
| `loading` | `True` | `dcc.Loading` around the graph |
| `theme` | `True` | follows the light/dark toggle from `theme_provider()` (plotly template; `data-theme` on `<html>` for your CSS) |
| `download` | `("png","html")` | toolbar buttons; add `"csv"` (needs `data.to_csv`) or pass `()` |
| `params` | `()` | `Param(name, component)` renders a control; `Param(name, id="x")` binds an existing one |
| `presets` | `True` | app-wide params (e.g. `a`, `b`) from `configure(presets=[Param(...)])`, put first in `params`. `False` or a list of names to opt out. Call `configure` before `Dash(use_pages=True)`. |
| `url` | `True` | mirrors every `Param` that has a component in the URL search string (`?a=a2&b=5`) via `history.replaceState`, and restores them on load. The theme is not in the URL: it persists in a `dcc.Store` with `storage_type="local"`. |
| `cache` | `0` | LRU of N `process` results by params (shared across users; `plot` must not mutate) |

`process` / `plot` / `layout` may accept fewer arguments (`plot=lambda df: ...`).

`plot` may return a Dash component instead of a figure (cards, tables, ...). It is rendered in place of the graph (still
inside `dcc.Loading`, still guarded by `errors`). Theming is then up to your CSS, and the `png` / `html` downloads don't apply, so
use `download=()` (or `("csv",)` if `process` returns something with `.to_csv`). If `plot` fails, the usual placeholder figure and alert show.

## Styling

No CSS ships with the library; style it yourself. Hooks: `data-theme="light|dark"` on `<html>`
(set by `theme_provider()`), and the classes `pp-theme`, `pp-page`, `pp-controls`, `pp-param`,
`pp-toolbar`, `pp-alert` (+ `pp-alert-error` / `pp-alert-warning`). Plots get a plotly template
from `theme.TEMPLATES`, which you can replace.

## Gotchas

- The function is named `register_page_plot` on purpose: Dash only auto-imports files in `pages/`
  that contain the text `register_page`. Don't alias it.
- Page keys/ids derive from `path`, so each page needs a distinct path key (a duplicate silently replaces the earlier page).
- With `theme=True`, `theme_provider()` must be in `app.layout`, or the callback has no store to read.
- URL values are typed from the component's default (`value=1` -> int, `value=[...]` -> JSON list), so give components a default. Params bound with `id=` only are not mirrored. For a URL-only param pass a store: `Param("n", dcc.Store(id="_", data=150), prop="data")` renders nothing, `?n=20` sets it (typed from `data`), and it is mirrored back like any other param. The id is a throwaway; `dcc.Store` just requires one. Presets are not carried across pages; links between pages must include the query string if you want that.
- Changing theme re-runs `process` unless `cache` is set.

## Example app

`example/` is a small multi-page app ("Meridian") on synthetic data. Each page shows different features:

| page | shows |
|---|---|
| `pages/home.py` | everything on by default, csv download, `cache`, a segmented radio, region/year presets |
| `pages/summary.py` | `plot` returns Dash components (KPI cards) instead of a figure, so no graph is rendered |
| `pages/breakdown.py` | slider + text filter, `UserError` for an empty search |
| `pages/cohorts.py` | sequential heatmap, a URL-only param (`?months=6`) |
| `pages/orders.py` | list-valued param (JSON in the URL), a control bound with `id=` from `layout()` |
| `pages/services.py` | `presets=False`, `download=("png",)`, a data source that fails (generic error alert) |

`chart_theme.py` registers light/dark plotly templates and points `theme.TEMPLATES` at them, so pages never mention colours.
`assets/style.css` styles the `pp-*` hooks.

Dev: `uv venv --python 3.11 && uv pip install -e ".[dev]"`, then `python -m pytest`; demo: `python example/app.py`.
The package must be installed (`-e .`) for the example and your own apps to import it.
