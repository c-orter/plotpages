"""Exercise the example app's generated callbacks through Flask's test client (no browser)."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "example"))
from app import app  # noqa: E402  (importing registers the example pages)

PRESETS = {"region": "All", "year": 2024}


@pytest.fixture(scope="module")
def client():
    app.server.testing = True
    return app.server.test_client()


def fire(client, output, values, mode="light"):
    """Invoke the callback whose output starts with `output`, as the Dash renderer would.

    `values` maps a param name (or a full component id) to its value; n_clicks is 1, the theme is `mode`.
    """
    deps = client.get("/_dash-dependencies").get_json()
    dep = next(d for d in deps if d["output"].startswith(output))
    key = output.strip(".").split("-")[0]

    def fill(item):
        name = item["id"].removeprefix(f"{key}-param-")
        if item["property"] == "n_clicks":
            value = 1
        elif item["property"] == "figure":
            value = values["figure"]
        elif item["id"] == "pp-theme":
            value = mode
        else:
            value = values[name]
        return {**item, "value": value}

    outs = [{"id": o.rsplit(".", 1)[0], "property": o.rsplit(".", 1)[1]} for o in dep["output"].strip(".").split("...")]
    inputs = [fill(i) for i in dep["inputs"]]
    body = {
        "output": dep["output"],
        "outputs": outs if len(outs) > 1 else outs[0],
        "inputs": inputs,
        "state": [fill(s) for s in dep.get("state", [])],
        "changedPropIds": [f"{inputs[0]['id']}.{inputs[0]['property']}"],
    }
    r = client.post("/_dash-update-component", json=body)
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    return r.get_json()["response"]


def plot(client, page, values, mode="light"):
    """Run a page's main callback -> (figure, alert)."""
    r = fire(client, f"..{page}-graph.figure", {**PRESETS, **values}, mode)
    return r[f"{page}-graph"]["figure"], r[f"{page}-error"]["children"]


OVERVIEW = {"granularity": "W", "metric": "revenue"}
BREAKDOWN = {"by": "product", "top_n": 5, "search": ""}
ORDERS = {"channels": ["Direct", "Online"], "orders-log": []}
SERVICES = {"env": "production", "window": 24}


def render_page(client, pathname, search):
    deps = client.get("/_dash-dependencies").get_json()
    dep = next(d for d in deps if d["output"].startswith("..") and "_pages_content" in d["output"])
    body = {
        "output": dep["output"],
        "outputs": [{"id": "_pages_content", "property": "children"}, {"id": "_pages_store", "property": "data"}],
        "inputs": [
            {"id": "_pages_location", "property": "pathname", "value": pathname},
            {"id": "_pages_location", "property": "search", "value": search},
        ],
        "changedPropIds": ["_pages_location.pathname"],
    }
    r = client.post("/_dash-update-component", json=body)
    assert r.status_code == 200
    return json.dumps(r.get_json()["response"]["_pages_content"]["children"]), r


def values(layout_json):
    """{component id: value} for every component in a serialised layout (controls and stores)."""
    out = {}

    def walk(n):
        if isinstance(n, dict):
            props = n.get("props", {})
            if "id" in props and ("value" in props or "data" in props):
                out[props["id"]] = props["value"] if "value" in props else props["data"]
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)

    walk(json.loads(layout_json))
    return out


# ---- every page works ------------------------------------------------------
@pytest.mark.parametrize(
    "page, params, traces",
    [
        ("home", OVERVIEW, 3),
        ("breakdown", BREAKDOWN, 1),
        ("cohorts", {"months": 12}, 1),
        ("orders", ORDERS, 3),
        ("services", SERVICES, 3),
    ],
)
def test_pages_render_a_figure(client, page, params, traces):
    fig, alert = plot(client, page, params)  # unused presets are ignored for pages that opt out
    assert len(fig["data"]) == traces and alert is None


def test_presets_reach_plot_and_filter(client):
    fig, _ = plot(client, "home", {**OVERVIEW, "region": "APAC"})
    visible = [t for t in fig["data"] if t.get("showlegend")]
    assert [t["name"] for t in visible] == ["APAC"]
    assert fig["data"][2]["name"] == "APAC"  # still third in order, so it keeps its colour slot


def test_theme_switches_template(client):
    light = plot(client, "home", OVERVIEW, "light")[0]["layout"]["template"]
    dark = plot(client, "home", OVERVIEW, "dark")[0]["layout"]["template"]
    assert light != dark and light["layout"]["paper_bgcolor"] == "#ffffff" and dark["layout"]["paper_bgcolor"] == "#09090b"


# ---- custom UI (plot returns a component) ----------------------------------
def test_component_result_replaces_graph(client):
    r = fire(client, "..summary-graph.figure", PRESETS)
    assert r["summary-graph"]["style"] == {"display": "none"} and "figure" not in r["summary-graph"]
    content = json.dumps(r["summary-content"]["children"])
    assert "kpi-value" in content and "vs 2023" in content and r["summary-error"]["children"] is None


def test_figure_result_shows_graph_and_clears_content(client):
    r = fire(client, "..home-graph.figure", {**PRESETS, **OVERVIEW})
    assert r["home-graph"]["style"] == {"height": "28rem"} and r["home-content"]["children"] is None


def test_component_page_error_falls_back_to_graph(client):
    r = fire(client, "..summary-graph.figure", {**PRESETS, "year": 1999})
    assert "No orders" in json.dumps(r["summary-error"]["children"])
    assert r["summary-graph"]["style"]["height"] and r["summary-content"]["children"] is None


# ---- error handling --------------------------------------------------------
def test_user_error_is_shown_as_warning(client):
    fig, alert = plot(client, "breakdown", {**BREAKDOWN, "search": "zzz"})
    assert "No products match" in json.dumps(alert) and "pp-alert-warning" in json.dumps(alert)
    assert "No products match" in json.dumps(fig["layout"]["annotations"])


def test_unexpected_error_is_caught(client):
    fig, alert = plot(client, "services", {**SERVICES, "env": "legacy"})
    assert "Something went wrong" in json.dumps(alert) and "pp-alert-error" in json.dumps(alert)
    assert "Could not draw" in json.dumps(fig["layout"]["annotations"])


def test_empty_selection_error(client):
    assert "at least one channel" in json.dumps(plot(client, "orders", {**ORDERS, "channels": []})[1])
    assert "No orders" in json.dumps(plot(client, "home", {**OVERVIEW, "year": 1999})[1])


# ---- layouts, URL restore, presets ----------------------------------------
def test_layouts_render(client):
    for path in ("/", "/summary", "/breakdown", "/cohorts", "/orders", "/services"):
        assert client.get(path).status_code == 200
    assert "pp-theme-toggle" in json.dumps(client.get("/_dash-layout").get_json())


def test_url_restores_presets_and_params(client):
    layout, _ = render_page(client, "/breakdown", "?region=EMEA&year=2023&top_n=5&by=channel&search=edge")
    v = values(layout)
    assert v["breakdown-param-region"] == "EMEA"
    assert v["breakdown-param-year"] == 2023 and isinstance(v["breakdown-param-year"], int)
    assert v["breakdown-param-top_n"] == 5 and v["breakdown-param-by"] == "channel"
    assert v["breakdown-param-search"] == "edge"
    d, _ = render_page(client, "/breakdown", "?year=oops")  # bad number -> default
    assert values(d)["breakdown-param-year"] == 2024 and values(d)["breakdown-param-region"] == "All"


def test_list_param_from_url(client):
    assert values(render_page(client, "/orders", '?channels=["Direct"]')[0])["orders-param-channels"] == ["Direct"]
    assert values(render_page(client, "/orders", "?channels=Online")[0])["orders-param-channels"] == ["Online"]


def test_url_only_param(client):
    layout, _ = render_page(client, "/cohorts", "?months=6")
    assert values(layout)["cohorts-param-months"] == 6  # typed from the store's data=12
    assert values(render_page(client, "/cohorts", "")[0])["cohorts-param-months"] == 12
    assert layout.count('"className": "pp-param"') == 2  # region + year; months renders nothing
    fig, _ = plot(client, "cohorts", {"months": 6})
    assert len(fig["data"][0]["x"]) == 7


def test_id_bound_param_reaches_plot(client):
    fig, _ = plot(client, "orders", {**ORDERS, "orders-log": ["log"]})
    assert fig["layout"]["yaxis"]["type"] == "log"
    assert plot(client, "orders", ORDERS)[0]["layout"]["yaxis"]["type"] == "linear"


def test_default_component_not_mutated_by_url(client):
    render_page(client, "/breakdown", "?region=EMEA")
    assert values(render_page(client, "/breakdown", "")[0])["breakdown-param-region"] == "All"


def test_opt_outs(client):
    deps = json.dumps(client.get("/_dash-dependencies").get_json())
    assert "services-param-region" not in deps and "services-file-html" not in deps  # presets=False, download=("png",)
    assert "home-file-csv" in deps and "services-urlsink.data" in deps and "cohorts-urlsink.data" in deps


# ---- downloads -------------------------------------------------------------
def test_csv_and_html_downloads(client):
    r = fire(client, "home-file-csv.data", {**PRESETS, **OVERVIEW})
    assert "date,region,revenue" in r["home-file-csv"]["data"]["content"].replace("region,date", "date,region")
    fig, _ = plot(client, "home", OVERVIEW)
    r = fire(client, "home-file-html.data", {"figure": fig})
    assert "<html" in r["home-file-html"]["data"]["content"]
