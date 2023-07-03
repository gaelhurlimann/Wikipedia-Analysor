from pprint import pprint
from urllib.parse import urlparse, unquote

DEFAULT_LANGS = ["en", "fr", "de"]


def extract_lang_name(link: str) -> tuple[str, str]:
    """
    Extract name and lang
    """
    if "//" not in link:
        link = f"//{link}"
    parsed = urlparse(link)
    lang = parsed.hostname.split(".")[0]
    name = parsed.path.split("/")[-1]
    return lang, unquote(name)


class Queries:
    def __init__(self, target_links, target_langs=None, verbose=False):
        self.verbose = verbose

        if target_langs is None:
            self.target_langs = set(DEFAULT_LANGS)
        else:
            self.target_langs = set(target_langs)

        self.target_links = set(target_links)

        self.to_find = {}
        self._init_links_to_find()

        self._queries = {}
        self._attributes = set()

    def _init_links_to_find(self):
        if not self.to_find:
            self.to_find = {}

        for link in self.target_links:
            # If it's a link, extract lang and name
            if "wikipedia.org" in link:
                lang, name = extract_lang_name(link)
                if lang not in self.to_find:
                    self.to_find[lang] = set()
                self.to_find[lang].add(name)
            # Else, we assume it's directly a name, and try to find it
            else:
                if "*" not in self.to_find:
                    self.to_find["*"] = set()
                self.to_find["*"].add(link)

        # Each name without a lang will be tracked down using target langs
        for name in self.to_find["*"]:
            for lang in self.target_langs:
                if lang not in self.to_find:
                    self.to_find[lang] = set()
                self.to_find[lang].add(name)

        del self.to_find["*"]

        if self.verbose:
            pprint(self.to_find)

    @property
    def attributes(self):
        return self._attributes

    def __getitem__(self, item):
        if item in self.target_langs:
            return self._queries[item]
        else:
            pass

    def __setitem__(self, key, value):
        raise AttributeError("Cannot change internal values.")
