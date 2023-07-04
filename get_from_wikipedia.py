import json
from datetime import datetime
from pprint import pprint
from urllib.parse import urlparse, unquote, quote

import requests


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


def qprint(json_queries):
    """
    Check if correct JSON and prints.
    """
    print(json.dumps(json_queries, indent=2))


def wiki_quote(page_name):
    """
    Transform into valid wiki URI.
    """
    return quote(page_name.replace(" ", "_"))


class Queries:
    # URLs
    URL_INFOS = "https://{lang}.wikipedia.org/w/api.php"
    URL_REST = "https://{lang}.wikipedia.org/w/rest.php/v1/search/title"
    # URL_STATS = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{lang}.wikipedia/{access}/{agent}/{uri_article_name}/{granularity}/{start}/{end}"

    # Request parameters
    HEADERS = {
        "User-Agent": "EPFL WikiStats",
        "From": "noreply@epfl.ch",
        "Accept": "json",
    }

    PARAMS = {
        "action": "query",
        "format": "json",
    }

    # Defaults
    DEFAULT_DURATION = int(2 * 365.25)
    DEFAULT_LANGS = ["en", "fr", "de"]

    # DEFAULT_ACCESS = "all-access"
    # DEFAULT_AGENTS = "all-agents"
    # DEFAULT_GRANULARITY = "daily"

    # API parameters
    GLOBAL_LIMIT = 25
    WIKI_LIMIT = 500  # From the API

    # Limits
    BACKLINKS_LIMIT = GLOBAL_LIMIT
    # CONTRIBS_LIMIT = WIKI_LIMIT

    def __init__(self, target_links, target_langs=None, verbose=False):
        self._verbose = verbose

        if target_langs is None:
            self.target_langs = set(self.DEFAULT_LANGS)
        else:
            self.target_langs = set(target_langs)

        self.target_links = set(target_links)

        self._init_links_to_find()

        self._queries = {}
        self._attributes = set()

        self._init_session()

    def _init_session(self):
        """
        Starts request session, that will be used through the whole process
        """
        self._s = requests.Session()
        self._s.headers.update(self.HEADERS)
        self._s.params.update(self.PARAMS)

    def _init_links_to_find(self):
        """
        Generate a list of tuples (lang, name) to find
        """
        self._to_find = {}

        for link in self.target_links:
            # If it's a link, extract lang and name
            if "wikipedia.org" in link:
                lang, name = extract_lang_name(link)
                if lang not in self._to_find:
                    self._to_find[lang] = set()
                self._to_find[lang].add(name)
            # Else, we assume it's directly a name, and try to find it
            else:
                if "*" not in self._to_find:
                    self._to_find["*"] = set()
                self._to_find["*"].add(link)

        # Each name without a lang will be tracked down using target langs
        for name in self._to_find["*"]:
            for lang in self.target_langs:
                if lang not in self._to_find:
                    self._to_find[lang] = set()
                self._to_find[lang].add(name)

        del self._to_find["*"]

        if self._verbose:
            print("== Queries: to find ==")
            pprint(self._to_find)

    @property
    def attributes(self):
        return self._attributes

    def __getitem__(self, item):
        if item in self.target_langs:
            temp = {}
            for name, obj in self._queries.items():
                if "error" in obj:
                    continue

                for lang, page in obj["langs"].items():
                    if lang == item:
                        if name not in temp:
                            temp[name] = obj
                        break
            return temp
        else:
            return self._queries[item].copy()

    def _immutable(self, *args, **kwargs):
        raise TypeError("Cannot change internal values.")

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    update = _immutable
    setdefault = _immutable
    pop = _immutable
    popitem = _immutable

    def _fetch_names(self):
        """
        Check if the page exists, gather information if it does

        https://www.mediawiki.org/wiki/API:Langlinks
        """
        for lang, names in self._to_find.items():
            url_full = self.URL_INFOS.format(lang=lang)
            # We group the queries per target lang for fewer queries
            titles = "|".join(names)
            params = {
                "titles": titles,
                "prop": "langlinks",
                "lllimit": self.WIKI_LIMIT,  # We want all langs in order to find our target langs
            }

            results = self._s.get(url=url_full, params=params)
            data = results.json()

            if "query" in data and "pages" in data["query"]:
                data = data["query"]["pages"]

                for pid, obj in data.items():
                    title = obj["title"]

                    # Will only keep the latest successful query for same name pages
                    self._queries[title] = {
                        "query": {
                            "lang": lang,
                        }
                    }

                    # Page was not found with that language
                    if int(pid) < 0:
                        self._queries[title]["error"] = "not found"
                        if self._verbose:
                            print(self._queries[title]["error"])
                        continue

                    self._queries[title]["query"].update({
                        "pid": int(pid),
                        "timestamp": datetime.today().isoformat(),
                        "duration": self.DEFAULT_DURATION,
                    })

                    # Add the query language in the list of langs
                    self._queries[title]["langs"] = {
                        lang: {
                            "name": title,
                        }
                    }

                    # Add the other target langs
                    if "langlinks" in obj:
                        for langlink in obj["langlinks"]:
                            if not self.target_langs or langlink["lang"] in self.target_langs:  # Use all langs if no target lang
                                self._queries[title]["langs"][langlink["lang"]] = {
                                    "name": langlink["*"]
                                }
        if self._verbose:
            print("== Queries: after retriving ==")
            qprint(self._queries)

        # Merge linked pages with different names
        # We assume here that pages are correctly linked (by Wikipedia) between each other
        next_queries = {}
        for name, obj in self._queries.items():
            if "error" in obj:
                next_queries[name] = obj
                continue

            skip = False
            for _, page in obj["langs"].items():
                if page["name"] in next_queries.keys():
                    skip = True
                    break

            if not skip:
                next_queries[name] = obj
        self._queries = next_queries

        if self._verbose:
            print("== Queries: after merging ==")
            qprint(self._queries)

        self._attributes.update(["name"])

    def _fetch_info(self):
        """
        Get some of the missing information, like pid and qwikidata

        Note: using revisions is a bit overkill, especially when actually retrieving revisions. However, quickest way
        to get creation date.

        https://www.mediawiki.org/wiki/API:Info
        https://www.mediawiki.org/wiki/API:Pageprops
        https://www.mediawiki.org/wiki/API:Revisions
        """
        for name, obj in self._queries.items():
            if "error" in obj:
                continue

            for lang, page in obj["langs"].items():
                url_full = self.URL_INFOS.format(lang=lang)
                params = {
                    "titles": page["name"],
                    "prop": "info|pageprops|revisions",
                    "inprop": "url",
                    "rvlimit": 1,
                    "rvprop": "timestamp|user",
                    "rvdir": "newer",
                }

                results = self._s.get(url=url_full, params=params)
                data = results.json()

                if "query" in data and "pages" in data["query"]:
                    content = data["query"]["pages"]
                    pid = next(iter(content))
                    page["pid"] = int(pid)
                    content = content[pid]
                    page["wikibase_item"] = content["pageprops"]["wikibase_item"]
                    page["length"] = content["length"]
                    page["url"] = content["canonicalurl"]
                    page["creation"] = {
                        "timestamp": content["revisions"][0]["timestamp"],
                        "user": content["revisions"][0]["user"],
                    }
                else:
                    obj["error"] = "could not retrieve information (info/pageprops/revisions)"
                    if self._verbose:
                        print(obj["error"])

        if self._verbose:
            print("== Queries: after pageprops ==")
            qprint(self._queries)

        self._attributes.update(["creation", "length", "url", "pid", "wikibase_item"])

    def _fetch_rest_description(self):
        """
        Get a short description for the page

        https://www.mediawiki.org/wiki/Extension:ShortDescription#Retrieve_short_description_through_REST_API
        https://www.mediawiki.org/wiki/API:REST_API/Reference
        """
        for name, obj in self._queries.items():
            if "error" in obj:
                continue

            for lang, page in obj["langs"].items():
                url_full = self.URL_REST.format(lang=lang)
                params = {
                    "q": page["name"],
                    "limit": 1,
                }

                results = self._s.get(url=url_full, params=params)
                data = results.json()

                if "pages" in data:
                    page["description"] = data["pages"][0]["description"]
                else:
                    obj["error"] = "could not retrieve information (rest description)"
                    if self._verbose:
                        print(obj["error"])

        if self._verbose:
            print("== Queries: after rest description ==")
            qprint(self._queries)

        self._attributes.update(["description"])

    def _fetch_backlinks(self):
        """
        Find backlinks for each page

        For important pages (looking at you, "École polytechnique fédérale de Lausanne"), can take some time!
        Set BACKLINKS_LIMIT to control that.

        https://www.mediawiki.org/wiki/API:Backlinks
        """
        for name, obj in self._queries.items():
            if "error" in obj:
                continue

            for lang, page in obj["langs"].items():
                blcontinue = ""
                blcounter = 0
                url_full = self.URL_INFOS.format(lang=lang)

                while blcounter < self.BACKLINKS_LIMIT:
                    params = {
                        "list": "backlinks",
                        "bltitle": page["name"],
                        "bllimit": min(self.BACKLINKS_LIMIT, self.WIKI_LIMIT),
                    }
                    if blcontinue != "":
                        params["blcontinue"] = blcontinue

                    results = self._s.get(url=url_full, params=params)
                    data = results.json()

                    if "query" in data and "backlinks" in data["query"]:
                        bldata = data["query"]["backlinks"]
                    else:
                        obj["error"] = "could not retrieve information (backlinks)"
                        break

                    if "backlinks" not in page:
                        page["backlinks"] = set()  # This is to delete doubles

                    if bldata:
                        for backlink in bldata:
                            page["backlinks"].add(backlink["title"])
                            blcounter += 1

                    if "continue" in data:
                        blcontinue = data["continue"]["blcontinue"]
                    else:
                        break

                if "backlinks" in page and isinstance(page["backlinks"], set):
                    page["backlinks"] = list(page["backlinks"])  # Sets are not valid JSON objects, lists are

        if self._verbose:
            print("== Queries: after backlinks ==")
            qprint(self._queries)

        self._attributes.update(["backlinks"])

    def _fetch_revisions(self):
        """
        Get revisions

        https://www.mediawiki.org/wiki/API:Revisions
        """

        for name, obj in self._queries.items():
            if "error" in obj:
                continue

            for lang, page in obj["langs"].items():
                url_full = self.URL_INFOS.format(lang=lang)
                params = {
                    "titles": page["name"],
                    "prop": "revisions",
                    "rvlimit": 1,
                    "rvprop": "timestamp|user",
                    "rvdir": "newer",
                }

                results = self._s.get(url=url_full, params=params)
                data = results.json()

                if "query" in data and "pages" in data["query"]:
                    content = data["query"]["pages"][pid]
                    pid = next(iter(content))
                    page["pid"] = int(pid)
                    content = content[pid]
                    page["pwikidata"] = content["pageprops"]["wikibase_item"]
                    page["creation"] = {
                        "timestamp": content["revisions"][0]["timestamp"],
                        "user": content["revisions"][0]["user"],
                    }
                else:
                    obj["error"] = "could not retrieve information (pageprops/revisions)"

        if self._verbose:
            print("== Queries: after revisions ==")
            qprint(queries)

        self._attributes.update(["revisions"])


if __name__ == "__main__":
    target_links = [
        "https://fr.wikipedia.org/wiki/Martin_Vetterli",
        "https://en.wikipedia.org/wiki/%C3%89cole_Polytechnique_F%C3%A9d%C3%A9rale_de_Lausanne",
        "https://en.wikipedia.org/wiki/Jean-Pierre_Hubaux",
        "https://it.wikipedia.org/wiki/Jean-Michel_LErreur",
        "https://fr.wikipedia.org/wiki/%C3%89cole_polytechnique_f%C3%A9d%C3%A9rale_de_Lausanne",
        "it.wikipedia.org/wiki/Jean-Michel_LErreur",
        "Michael_Grätzel",
        "Patrick Aebischer",
    ]

    queries = Queries(target_links, verbose=True)
    queries._fetch_names()
    queries._fetch_info()
    queries._fetch_rest_description()
