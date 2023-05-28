import hashlib

LANGS = {
    "fr": "Français",
    "en": "English",
    "de": "Deutsch",
    "it": "Italiano"
}


# https://stackoverflow.com/a/1094933
def sizeof_fmt(num, suffix="B"):
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"


def get_color(lang):
    m = hashlib.sha256()
    m.update(lang.encode())
    return f"#{m.hexdigest()[:6]}"
