import hashlib


LANGS = {"fr": "Français", "en": "English", "de": "Deutsch", "it": "Italiano"}


# https://stackoverflow.com/a/1094933
def sizeof_fmt(num, suffix="B", sign=False):
    if abs(num) < 1024.0:
        return f"{num:+3.0f}{suffix}" if sign else f"{num:+3.0f}{suffix}"
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return f"{num:+3.1f}{unit}{suffix}" if sign else f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:+.1f}Yi{suffix}" if sign else f"{num:.1f}Yi{suffix}"


def humantime_fmt(t):
    if t < 60.0:
        return f"{t:2.0f}s"
    elif t < 60.0 * 60.0:
        return f"{t // 60:2.0f}min {t % 60:2.0f}s"


def get_color(lang):
    m = hashlib.sha256()
    m.update(lang.encode())
    return f"#{m.hexdigest()[:6]}"


def map_score(value, min_value, max_value, min_score=1, max_score=6):
    """
    Map a value from a range to another range.

    :param value:
    :param min_value:
    :param max_value:
    :param min_score:
    :param max_score:
    :return:
    """
    span_value = max_value - min_value
    span_score = max_score - min_score
    scaled_value = float(value - min_value) / float(span_value)
    return min_score + (scaled_value * span_score)

def create_main_fig(fig_main):
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
