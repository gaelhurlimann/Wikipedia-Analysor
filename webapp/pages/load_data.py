import base64
import csv
import json


from dash import callback, dcc, html, Input, Output, State
import dash
import dash_bootstrap_components as dbc
import requests


from get_from_wikipedia import get_from_wikipedia


dash.register_page(__name__, path="/")

layout = dbc.Container(
    [
        html.H2("Input your Wikipedia pages"),
        html.P("Can be either a full link, or a page name. One article per row."),
        html.Br(),
        # Text input
        html.H3("Copy-paste your inputs"),
        dbc.Form(
            [
                dbc.Textarea(
                    id="input_text",
                    className="mb-3",
                    placeholder="https://fr.wikipedia.org/wiki/École_polytechnique_fédérale_de_Lausanne\nen.wikipedia.org/wiki/Jean-Pierre_Hubaux\nMichael Grätzel",
                ),
                dbc.Button("Submit", id="submit_text", color="primary"),
            ]
        ),
        html.Br(),
        # File input
        html.H3("Or, upload a file"),
        dcc.Upload(
            id="input_file",
            children=html.Div(["Drag and Drop or ", html.A("Select Files")]),
            style={
                "width": "100%",
                "height": "60px",
                "lineHeight": "60px",
                "borderWidth": "1px",
                "borderStyle": "dashed",
                "borderRadius": "5px",
                "textAlign": "center",
            },
            # Allow multiple files to be uploaded
            multiple=False,
        ),
        html.Div(id="output-data-upload"),
        html.Br(),
        # GSheet input
        html.H3("Or, provide a link to a Google Sheet"),
        dbc.Form(
            [
                dbc.Input(
                    id="input_gsheet",
                    className="mb-3",
                    placeholder="https://docs.google.com/spreadsheets/d/ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdefgh/edit",
                    type="text",
                ),
                dbc.Button("Submit", id="submit_gsheet", color="primary"),
            ]
        ),
        # Result
        html.Center(dbc.Spinner(html.Div(id="spinner"), id="spinner-out", color="primary")),
        html.Div(
            [
                html.Hr(),
                html.H2("Resulting query"),
                dbc.Textarea(
                    id="queries-text",
                    className="mb-3",
                    placeholder="{}",
                ),
                html.Center(
                    [
                        html.A(dbc.Button("Global dashboard", size="lg", className="me-1"), href="dashboard"),
                        html.A(dbc.Button("Article dashboard", size="lg", className="me-1"), href="individual"),
                        dbc.Button("Download resulting query", id="queries-dl", size="lg", className="me-1"),
                    ]
                ),
            ],
            id="queries",
        ),
    ]
)


@callback(
    Output("data", "data"),
    Output("spinner", "children"),
    Input("submit_text", "n_clicks"),
    Input("input_text", "value"),
)
def process_text(n, value):
    if n is not None:
        target_links = value.split("\n")
        queries = get_from_wikipedia(target_links)
        print("Done with processing text")
        return queries, "Done with processing text"
    else:
        return None, None


@callback(
    Output("data", "data", allow_duplicate=True),
    Output("spinner", "children", allow_duplicate=True),
    Input("input_file", "contents"),
    State("input_file", "filename"),
    State("input_file", "last_modified"),
    prevent_initial_call="initial_duplicate",
)
def process_file(content, name, date):
    if content is not None:
        content_type, content_string = content.split(",")
        target_links = base64.b64decode(content_string).decode().replace("\r", "").split("\n")
        queries = get_from_wikipedia(target_links)
        print("Done with processing file")
        return queries, "Done with processing file"
    else:
        return None, None


@callback(
    Output("data", "data", allow_duplicate=True),
    Output("spinner", "children", allow_duplicate=True),
    Input("submit_gsheet", "n_clicks"),
    Input("input_gsheet", "value"),
    prevent_initial_call="initial_duplicate",
)
def process_gsheet(n, value):
    if n is not None:
        csv_url = value.replace("edit", "export?format=csv")

        res = requests.get(url=csv_url)
        if res.status_code != 200:
            return None, None
        else:
            res.encoding = res.apparent_encoding  # So that we get properly encoded results
            target_links = [link[0] for link in csv.reader(res.text.strip().split("\n"))]

        queries = get_from_wikipedia(target_links)
        print("Done with processing gsheet")
        return queries, "Done with processing gsheet"
    else:
        return None, None


@callback(
    Output("queries-text", "value"),
    Output("queries", "style"),
    Input("data", "data"),
)
def show_query(data):
    if data is not None:
        return json.dumps(data, indent=2, ensure_ascii=False), {"display": "inline"}
    else:
        return None, {"display": "none"}
