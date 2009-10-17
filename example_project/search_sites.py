# Auto-discover all `search_indexes.py` and register.
# Most of the time, this is what you want.
import haystack
haystack.autodiscover()


# Advanced `SearchSite` creation/registration. Rarely needed.
# from haystack.sites import SearchSite
# from bare_bones_app.models import Cat
# mysite = SearchSite()
# mysite.register(Cat)
# ... or ...
# from bare_bones_app.search_indexes import CatIndex
# mysite.register(Cat, CatIndex)
