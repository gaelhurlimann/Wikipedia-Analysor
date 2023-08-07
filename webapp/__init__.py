from dash import Dash, dcc, html
import dash
import dash_bootstrap_components as dbc


app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    use_pages=True,
    suppress_callback_exceptions=True,
)

app.layout = dbc.Container(
    [
        dcc.Store(id="data", storage_type="session"),
        dcc.Location(id="url", refresh=True),
        dcc.Download(id="download"),
        # Header
        html.Center(html.H1("Wikipedia Analysor")),
        html.Hr(),
        dbc.Alert(
            children="",
            id="alert",
            color="warning",
            is_open=False,
            duration=4000,
        ),
        dash.page_container,
        # Footer
        html.Hr(),
        html.Center(
            html.P(
                [
                    "Made with ❤️, available on ",
                    html.A("GitHub", href="https://github.com/Amustache/Wikipedia-Analysor", target="_blank"),
                ]
            )
        ),
    ]
)

# Debug
if __name__ == "__main__":
    app.run(debug=True)
