from datetime import datetime
import json


from dash import callback, Dash, dash_table, dcc, html, Input, Output, State
from plotly import express as px
from plotly import graph_objects as go
import dash
import dash_bootstrap_components as dbc
import pandas as pd


from webapp.helpers import get_color, humantime_fmt, LANGS, map_score, sizeof_fmt


dash.register_page(__name__)

layout = dbc.Container(
    [
        # Dropdowns (person & lang)
        dbc.Row(
            [
                dbc.Col(
                    dcc.Dropdown(
                        id="person",
                        options=["hihihi", "hahaha", "hohoho"],  # Else, it breaks...
                        value="hihihi",
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


@callback(
    Output("person", "options"),
    Output("person", "value"),
    Input("data", "data"),
)
def load_data(data):
    if data is not None:
        people = list(data.keys())
        return people, people[0]


@callback(
    Output("langs", "options"),
    Output("langs", "value"),
    Input("person", "value"),
    State("data", "data"),
)
def change_person(person, data):
    cur_data = data[person]

    if "error" in cur_data:
        return [], ""
    langs = list(cur_data["langs"])

    return langs, langs[0]


@callback(
    Output("by-lang", "children"),
    State("person", "value"),
    Input("langs", "value"),
    State("data", "data"),
)
def update_by_lang(selected_person, selected_langs, data):
    """
    Add a row to contain language details, such as contributions, for each language selected.
    """
    if "error" in data[selected_person]:
        return []

    cur_data = data[selected_person]["langs"]

    if not isinstance(selected_langs, list):
        selected_langs = [selected_langs]

    by_langs = []
    for lang in selected_langs:
        # Infos card
        name = cur_data[lang]["name"]
        link = f"https://{lang}.wikipedia.org/wiki/{name.replace(' ', '_')}"
        creation_user = cur_data[lang]["creation"]["user"]
        creation_user_link = f"https://{lang}.wikipedia.org/wiki/User:{creation_user}"

        readability = [
            html.H5("Readability"),
            html.Dt("Stats"),
            html.Dd(
                [
                    cur_data[lang]["stats"]["num_words"],
                    " words, ",
                    cur_data[lang]["stats"]["num_sentences"],
                    " sentences, ",
                    "takes ",
                    humantime_fmt(cur_data[lang]["stats"]["reading_time"]),
                    " to read.",
                ]
            ),
        ]
        for obj in cur_data[lang]["readability"].values():
            readability.append(html.Dt(html.A(obj["name"], href=obj["link"], target="_blank")))
            percent = map_score(obj["result"], obj["min"], obj["max"], 0, 100)  # min is harder to read
            if percent < 30:
                colour = "danger"
            elif percent > 60:
                colour = "success"
            else:
                colour = "warning"
            hint = f"{'Lower' if obj['min'] > obj['max'] else 'Higher'} value means the article is easier to read (from {obj['min']} to {obj['max']})."
            readability.append(
                html.Dd(
                    [
                        hint,
                        dbc.Progress(label=obj["result"], value=percent, color=colour),
                    ]
                )
            )

        card = dbc.Card(
            [
                dbc.CardHeader(f"{lang} - {LANGS[lang]}"),
                dbc.CardBody(
                    [
                        html.A(html.H4(name, className="card-title"), href=link, target="_blank"),
                        html.P(cur_data[lang]["description"] or "(no short description found)", className="card-text"),
                        html.Dl(
                            [
                                html.Dt("Page creation"),
                                html.Dd(
                                    html.P(
                                        [
                                            datetime.fromisoformat(
                                                cur_data[lang]["creation"]["timestamp"].replace("Z", "+00:00")
                                            ).strftime("%Y-%m-%d %H:%M"),
                                            ", by ",
                                            html.A(creation_user, href=creation_user_link, target="_blank"),
                                        ]
                                    ),
                                ),
                                html.Dt("Unique (named) contributors"),
                                html.Dd(len(set(cur_data[lang]["contributors"]))),
                                html.Dt("Unique (internal) backlinks"),
                                html.Dd(len(set(cur_data[lang]["backlinks"]))),
                            ]
                            + readability,
                        ),
                    ]
                ),
            ],
            style={"width": "18rem"},
        )

        # Contributions table
        data = cur_data[lang]["contributions"]["items"]
        data.reverse()

        try:
            prev_size = None
            for d in data:
                d.update(
                    {
                        "timestamp": datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00")).strftime(
                            "%Y-%m-%d %H:%M"
                        ),
                        "change": sizeof_fmt(d["size"] - prev_size if prev_size else 0, sign=True),
                    }
                )
                prev_size = d["size"]
                d.update({"size": sizeof_fmt(d["size"])})
        except TypeError:  # Already done
            pass

        columns = [
            {
                "name": "Timestamp (UTC)",
                "id": "timestamp",
            },
            {
                "name": "Username or IP address",
                "id": "username",
            },
            {
                "name": "Size change",
                "id": "change",
            },
            {
                "name": "Resulting size",
                "id": "size",
            },
        ]
        table = dbc.Card(
            [
                dbc.CardHeader(f"List of contributions"),
                dbc.CardBody(
                    [
                        dash_table.DataTable(
                            id=f"table-{lang}",
                            data=data,
                            columns=columns,
                            sort_action="native",
                            filter_action="native",
                            page_size=10,
                            style_cell_conditional=[
                                {"if": {"column_id": "timestamp"}, "width": "40%"},
                                {"if": {"column_id": "username"}, "width": "40%"},
                            ],
                        ),
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
            ],
        )
        by_langs.append(row_lang)

    return by_langs


@callback(
    Output("graph", "figure"),
    Output("graph", "style"),
    State("person", "value"),
    Input("langs", "value"),
    State("data", "data"),
)
def update_graph(selected_person, selected_langs, data):
    """
    Update the graph with one or multiple languages.
    """
    if "error" in data[selected_person]:
        return go.Figure(), {"display": "none"}

    cur_data = data[selected_person]["langs"]

    if not isinstance(selected_langs, list):
        selected_langs = [selected_langs]

    figs = list()
    for lang in selected_langs:
        pageviews_en = cur_data[lang]["pageviews"]["items"]  # "timestamp", "views"
        df = pd.read_json(json.dumps(pageviews_en))

        fig_line = px.line(df, x="timestamp", y="views")
        fig_line.update_traces(line_color=get_color(lang))

        figs.append(fig_line)
    try:
        figs = iter(figs)
        figs_data = next(figs).data
    except StopIteration:  # There is no data
        return go.Figure(), {"display": "none"}

    for fig in figs:
        figs_data += fig.data

    fig_main = go.Figure(data=figs_data)

    for lang in selected_langs:
        contributions = cur_data[lang]["contributions"]["items"]
        for contrib in contributions:
            fig_main.add_vline(x=contrib["timestamp"], line_dash="dash", line_color=get_color(lang))

    fig_main.update_xaxes(
        rangeslider_visible=True,
        rangeselector=dict(
            buttons=list(
                [
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                    dict(count=1, label="1y", step="year", stepmode="backward"),
                    dict(step="all"),
                ]
            )
        ),
    )

    return fig_main, {"display": "inline"}
