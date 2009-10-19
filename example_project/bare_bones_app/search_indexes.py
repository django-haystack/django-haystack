from haystack import site
from bare_bones_app.models import Cat

# For the most basic usage, you can simply register a model with the `site`.
# It will get a `haystack.indexes.BasicSearchIndex` assigned to it, whose
# only requirement will be that you create a
# `search/indexes/bare_bones_app/cat_text.txt` data template for indexing.
site.register(Cat)
