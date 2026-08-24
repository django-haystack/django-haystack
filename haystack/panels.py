from debug_toolbar.panels import Panel
from django.utils.translation import gettext_lazy as _

from haystack import connections


class HaystackDebugPanel(Panel):
    """
    Panel that displays information about the Haystack queries run while
    processing the request.
    """

    name = "Haystack"
    has_content = True
    template = "panels/haystack.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._offset = {
            alias: len(connections[alias].queries)
            for alias in connections.connections_info.keys()
        }
        self._search_time = 0
        self._queries = []
        self._backends = {}

    @property
    def title(self):
        return _("Haystack Queries")

    @property
    def nav_subtitle(self):
        self._queries = []
        self._backends = {}

        for alias in connections.connections_info.keys():
            search_queries = connections[alias].queries[self._offset[alias] :]
            self._backends[alias] = {
                "time_spent": sum(float(q["time"]) for q in search_queries),
                "queries": len(search_queries),
            }
            self._queries.extend([(alias, q) for q in search_queries])

        self._queries.sort(key=lambda x: x[1]["start"])
        self._search_time = sum([d["time_spent"] for d in self._backends.values()])
        num_queries = len(self._queries)
        return "%d %s in %.2fms" % (
            num_queries,
            (num_queries == 1) and "query" or "queries",
            self._search_time,
        )

    def get_stats(self):
        width_ratio_tally = 0

        for alias, query in self._queries:
            query["alias"] = alias
            query["query"] = query["query_string"]

            if query.get("additional_kwargs"):
                if query["additional_kwargs"].get("result_class"):
                    query["additional_kwargs"]["result_class"] = str(
                        query["additional_kwargs"]["result_class"]
                    )

            try:
                query["width_ratio"] = (float(query["time"]) / self._search_time) * 100
            except ZeroDivisionError:
                query["width_ratio"] = 0

            query["start_offset"] = width_ratio_tally
            width_ratio_tally += query["width_ratio"]

        return {
            "backends": sorted(
                self._backends.items(), key=lambda x: -x[1]["time_spent"]
            ),
            "queries": [q for a, q in self._queries],
            "sql_time": self._search_time,
        }
