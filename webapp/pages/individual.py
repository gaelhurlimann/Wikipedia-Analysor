from datetime import datetime
import io
import json


from dash import callback, Dash, dash_table, dcc, html, Input, Output, State
from plotly import express as px
from plotly import graph_objects as go
import dash
import dash_bootstrap_components as dbc
import pandas as pd


from webapp.helpers import create_main_fig, get_color, get_textcolor, humantime_fmt, LANGS, map_score, sizeof_fmt


dash.register_page(__name__)

layout = dbc.Container(
    [
        html.H2("", id="page_title"),
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
                    html.H3(
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
        html.H3(
            "Detail per language",
            style={"margin-bottom": "1em"},
        ),
        html.Div(id="by-lang"),
        html.Center(
            [
                html.A(dbc.Button("Global dashboard", size="lg", className="me-1"), href="dashboard"),
                html.A(dbc.Button("Article dashboard", size="lg", className="me-1"), href="individual"),
            ]
        ),
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
    Output("page_title", "children"),
    Input("person", "value"),
    State("data", "data"),
)
def change_person(person, data):
    cur_data = data[person]

    if "error" in cur_data:
        return [], "", f"Error with {person}"
    langs = list(cur_data["langs"])

    return langs, langs[0], person


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

        class_importance = [
            html.H5(
                html.A(
                    "Class and importance",
                    href="https://en.wikipedia.org/wiki/Wikipedia:Content_assessment",
                    target="_blank",
                )
            ),
        ]
        # We have this to assure readability of the in the badge (no white text on yellow bkgnd)
        if "pageassessments" in cur_data[lang]:
            for category, obj in cur_data[lang]["pageassessments"].items():
                class_importance.append(html.Dt(category))
                cnt = []
                if "class" in obj and obj["class"] != "":
                    cnt.append(dbc.Badge(obj["class"], color=get_color(obj["class"]), text_color=get_textcolor(obj["class"])))
                if "importance" in obj and obj["importance"] != "":
                    cnt.append(dbc.Badge(obj["importance"], color=get_color(obj["importance"])))
                class_importance.append(html.Dd(html.Span(cnt)))
        else:
            class_importance.append(html.P("Not available."))

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

        len_contributors = len(set(cur_data[lang]["contributors"]))
        len_backlinks = len(set(cur_data[lang]["backlinks"]))
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
                                html.Dd(
                                    len_contributors
                                    if len_contributors < CONTRIBS_LIMIT
                                    else f"More than {CONTRIBS_LIMIT}"
                                ),
                                html.Dt("Unique (internal) backlinks"),
                                html.Dd(
                                    html.A(
                                        len_backlinks
                                        if len_backlinks < BACKLINKS_LIMIT
                                        else f"More than {BACKLINKS_LIMIT}",
                                        href=f"https://{lang}.wikipedia.org/wiki/Special:WhatLinksHere/{name.replace(' ', '_')}",
                                        target="_blank",
                                    )
                                ),
                            ]
                            + class_importance
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
            first_id = data[-1]["revid"]
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

                # Diff link
                actu = (
                    f"[actu](https://{lang}.wikipedia.org/w/index.php?title={name.replace(' ', '_')}&diff={first_id}&oldid={d['revid']})"
                    if first_id != d["revid"]
                    else "actu"
                )
                diff = f"[diff](https://{lang}.wikipedia.org/w/index.php?title={name.replace(' ', '_')}&diff=prev&oldid={d['revid']})"
                d.update({"links": f"({actu} | {diff})"})
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
            {
                "name": "",
                "id": "links",
                "presentation": "markdown",
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
        df = pd.read_json(io.StringIO(json.dumps(pageviews_en)))

        fig_line = px.line(df, x="timestamp", y="views", hover_name=len(df) * [get_lang_name(lang)])
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

    return create_main_fig(fig_main)
