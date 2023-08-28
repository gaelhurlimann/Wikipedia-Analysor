import json

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import html, dcc, callback, Input, Output, State
from plotly import graph_objects as go
from plotly import express as px

from get_from_wikipedia import DEFAULT_LANGS
from webapp.helpers import get_color, create_main_fig

dash.register_page(__name__)

layout = dbc.Container([
    html.H2("Dashboard"),
    html.Br(),

    dbc.Row([
        html.H3("Top 5 pages"),
        html.P("According to their number of page views."),
        html.Ul([], id="top-names"),
        dbc.Col([
            dcc.Dropdown(
                id="top-langs",
                options=DEFAULT_LANGS,
                value=DEFAULT_LANGS[0],
                clearable=False,
            ),
            dcc.Graph(
                id="top-graph"
            ),
            html.P(id="debug"),
        ]),
    ]),

    # dbc.Row([
    #     html.H3("Total page views"),
    #     html.P("All the pages, all the languages."),
    #     dbc.Col([
    #         dcc.Graph(
    #             id="total-graph"
    #         )
    #     ]),
    # ]),
])


@callback(
    Output("top-graph", "figure"),
    Output("top-graph", "style"),
    # Output("top-names", "children"),
    Input("top-langs", "value"),
    State("data", "data")
)
def update_top5(selected_lang, data):
    tops = []
    for person, content in data.items():
        if "error" in content:
            print("error")
            continue

        for lang, obj in content["langs"].items():
            if lang != selected_lang:
                continue

            print(f"current: {person}/{lang}")
            if len(tops) < 5:
                tops.append({
                    "name": obj["name"],
                    "pageviews_total": obj["pageviews_total"],
                    "pageviews_en": obj["pageviews"]["items"],  # "timestamp", "views"
                })
            else:
                # If last object has less pageview, replace
                if obj["pageviews_total"] > tops[-1]["pageviews_total"]:
                    tops[-1] = {
                        "name": obj["name"],
                        "pageviews_total": obj["pageviews_total"],
                        "pageviews_en": obj["pageviews"]["items"],  # "timestamp", "views"
                    }
            tops = sorted(tops, key=lambda x: x["pageviews_total"])

    figs = list()
    for top in tops:
        df = pd.read_json(json.dumps(top["pageviews_en"]))
        fig_line = px.line(df, x="timestamp", y="views")
        fig_line.update_traces(line_color=get_color(top["name"]))
        figs.append(fig_line)

    try:
        figs = iter(figs)
        figs_data = next(figs).data
    except StopIteration:  # There is no data
        return go.Figure(), {"display": "none"}  #, None

    for fig in figs:
        figs_data += fig.data

    fig_main = go.Figure(data=figs_data)

    fig, style = create_main_fig(fig_main)

    return fig, style  #, [html.Li(f"{top['name']}: {top['pageviews_total']} views" for top in tops)]
