import json

import pandas as pd
from dash import Dash, html, dcc, Output, Input, State, dash_table
import dash_bootstrap_components as dbc
from plotly import graph_objects as go, express as px

from webapp.data import PEOPLE, DATA
from webapp.helpers import LANGS, get_color

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.layout = dbc.Container(
    [
        # Header
        html.H1("Wikipedia Analysor"),
        html.Hr(),
        dbc.Alert(
            children="",
            id="alert",
            color="warning",
            is_open=False,
            duration=4000,
        ),

        # Dropdowns (person & lang)
        dbc.Row(
            [
                dbc.Col(
                    dcc.Dropdown(
                        id="person",
                        options=PEOPLE,
                        value=PEOPLE[0],
                        clearable=False,
                    ),
                    width={"size": 6, "offset": 0},
                ),
                dbc.Col(
                    dcc.Dropdown(
                        id="langs",
                        options=[],
                        value="",
                        clearable=False,
                        multi=True,
                    ),
                    width={"size": 6, "offset": 0},
                ),
            ]
        ),

        # Graph
        dbc.Row(
            dbc.Col(
                [
                    html.H2(
                        "Number of page views by language",
                        style={"margin-bottom": "1em"},
                    ),
                    dcc.Graph(
                        id="graph",
                    ),
                ]
            ),
        ),

        # By language
        html.H2(
            "Detail per language",
            style={"margin-bottom": "1em"},
        ),
        html.Div(id="by-lang"),
    ],
    fluid="xl",
)


@app.callback(
    Output("langs", "options"),
    Output("langs", "value"),
    Input("person", "value"),
)
def change_person(person):
    cur_data = DATA[person]

    if "error" in cur_data:
        return [], ""
    langs = list(cur_data["langs"])

    return langs, langs[0]


@app.callback(
    Output("by-lang", "children"),
    State("person", "value"),
    Input("langs", "value"),
)
def update_by_lang(selected_person, selected_langs):
    """
    Add a row to contain language details, such as contributions, for each language selected.
    """
    cur_data = DATA[selected_person]["langs"]

    if not isinstance(selected_langs, list):
        selected_langs = [selected_langs]

    by_langs = []
    for lang in selected_langs:
        # Infos card
        name = cur_data[lang]["name"]
        link = f"https://{lang}.wikipedia.org/wiki/{name.replace(' ', '_')}"
        creation_user = cur_data[lang]['creation']['user']
        creation_user_link = f"https://{lang}.wikipedia.org/wiki/User:{creation_user}"

        card = dbc.Card(
            [
                dbc.CardHeader(f"{lang} - {LANGS[lang]}"),
                dbc.CardBody(
                    [
                        html.H4(name, className="card-title"),
                        html.P("This is some placeholder text", className="card-text"),
                        html.Dl(
                            [
                                html.Dt("Link"),
                                html.Dd(html.A(link, href=link, target="_blank")),

                                html.Dt("Page creation"),
                                html.Dd(cur_data[lang]["creation"]["timestamp"]),

                                html.Dt("Page creator"),
                                html.Dd(html.A(creation_user, href=creation_user_link, target="_blank")),

                                html.Dt("Unique (named) contributors"),
                                html.Dd(len(set(cur_data[lang]["contributors"]))),

                                html.Dt("Unique (internal) backlinks"),
                                html.Dd(len(set(cur_data[lang]["backlinks"]))),
                            ],
                        )
                    ]
                ),
            ],
            style={"width": "18rem"},
        )

        # Contributions table
        data = cur_data[lang]["contributions"]["items"]
        columns = [{"name": i, "id": i} for i in data[0].keys()]
        table = dbc.Card(
            [
                dbc.CardHeader(f"List of contributions"),
                dbc.CardBody(
                    [
                        dash_table.DataTable(id=f"table-{lang}", data=data, columns=columns),
                    ],
                ),
            ],
        )

        row_lang = dbc.Row(
            id=f"lang-{lang}",
            style={"margin-bottom": "2em"},
            children=[
                dbc.Col(
                    width=3,
                    children=card,
                ),
                dbc.Col(
                    width=9,
                    children=table,
                ),
            ]
        )
        by_langs.append(row_lang)

    return by_langs


@app.callback(
    Output("graph", "figure"),
    Output("graph", "style"),
    State("person", "value"),
    Input("langs", "value"),
)
def update_graph(selected_person, selected_langs):
    """
    Update the graph with one or multiple languages.
    """
    cur_data = DATA[selected_person]["langs"]

    if "error" in cur_data:
        return go.Figure(), {'display': 'none'}

    if not isinstance(selected_langs, list):
        selected_langs = [selected_langs]

    figs = list()
    for lang in selected_langs:
        pageviews_en = cur_data[lang]["pageviews"]["items"]  # "timestamp", "views"
        df = pd.read_json(json.dumps(pageviews_en))

        fig_line = px.line(df, x='timestamp', y='views')
        fig_line.update_traces(line_color=get_color(lang))

        figs.append(fig_line)

    try:
        figs = iter(figs)
        figs_data = next(figs).data
    except StopIteration:  # There is no data
        return go.Figure(), {'display': 'none'}

    for fig in figs:
        figs_data += fig.data

    fig_main = go.Figure(data=figs_data)

    fig_main.update_xaxes(
        rangeslider_visible=True,
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1m", step="month", stepmode="backward"),
                dict(count=6, label="6m", step="month", stepmode="backward"),
                dict(count=1, label="YTD", step="year", stepmode="todate"),
                dict(count=1, label="1y", step="year", stepmode="backward"),
                dict(step="all")
            ])
        )
    )

    return fig_main, {'display': 'inline'}
