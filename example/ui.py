from dash import html


def page_header(title: str, description: str) -> html.Div:
    return html.Div([html.H1(title), html.P(description)], className="page-header")
