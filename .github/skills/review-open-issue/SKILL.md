---
name: Review an open Whoosh-related issue
description: >-
  A repeatable rubric for triaging django-haystack issues that involve the
  Whoosh search backend. Buckets each issue by root cause so it can be routed,
  answered, or closed quickly, and separates true Whoosh-library behavior from
  Haystack-integration bugs and other backends.
---

# Reviewing an open Whoosh-related issue

Many open issues mention "Whoosh" only in passing. The goal of a review pass is
to decide, for each issue, **where the root cause actually lives** and give the
reporter a concrete next step. Work through the buckets below in order; the
first one that fits is usually the right home for the issue.

## Quick decision tree
Before deep-reading, run each issue through this in order and stop at the first
"yes":

1. Does the report name a **different backend** (Elasticsearch/Solr/Xapian/PG)?
   → bucket 6, *Not Whoosh*.
2. Is the failing surface a **Haystack construct** (`SearchQuerySet` caching,
   pagination, templates, `SimpleLazyObject`) with no Whoosh traceback?
   → bucket 6, *Haystack layer*.
3. Does it involve **what got indexed vs. what matched** (stemming, accents,
   CJK, n-grams, wildcards, `__contains`)? → bucket 1 or 2.
4. Is it about **ranking/order** of otherwise-correct hits? → bucket 3.
5. Is it about **speed**? → bucket 4.
6. Is it a **lock / "already in a doc" / multi-worker** error? → bucket 5.

## 1. Analysis / tokenization
Symptoms: unexpected stemming, accented characters not matching, CJK/non-English
tokenization, n-gram sizing, field-name collisions.

- Whoosh analyzers are **composable and per-field**
  (`Tokenizer | Filter | Filter`), so most of these are configuration, not bugs.
- Stemming surprises (e.g., `Sodenthaler → sodenthal`) → the field should let the
  user opt in to `StemmingAnalyzer` rather than have it hardcoded.
- Accent/character folding → `StandardAnalyzer() | CharsetFilter(accent_map)`.
- Non-English / CJK → wrap a custom tokenizer (jieba, MeCab) or use `NGRAM`.
- N-gram sizing → `NGRAM(minsize, maxsize)` / `NGRAMWORDS(...)` constructor args.

## 2. Query parsing / reserved characters
Symptoms: hyphens, quotes, leading `-`, `__contains` returning nothing.

- Usually the **backend's own escaping / `clean()`**, not Whoosh's parser.
- Prefer building queries with `whoosh.query` objects or a configured
  `QueryParser` + plugins over string-munging that must then be re-escaped.
- `__contains` → a `*term*` wildcard, which will **not** match a stemmed field;
  it needs a keyword/non-stemmed field.

## 3. Scoring / boosting
Symptoms: field boosts ignored, `order_by('score')` not working.

- whoosh3 scores with **BM25F**; per-field boosts via
  `MultifieldParser(fieldboosts=...)` and schema `boost=`.
- Results already come back in descending score order; adding a `sortedby`
  field disables relevance ranking unless explicitly combined.
- Confirm the backend in the report is actually Whoosh (many boost reports are
  Elasticsearch).

## 4. Performance
Symptoms: slow search, slow iteration, slow spelling suggestions.

- Spelling slowness → use whoosh3's `Corrector` / `results.corrected_string()`,
  scope suggestions to specific fields, reuse a cached reader.
- Slow iteration → reuse **one** searcher/reader per request; page with
  `search_page` instead of re-opening per hit.

## 5. Locking / concurrency
Symptoms: lock not released, "start_doc when already in a doc", multi-worker
indexing failures.

- Whoosh is **single-writer** (a `FileStorage` lock); concurrent writers must
  serialize. Use `writer(timeout=..., delay=...)` or a buffered writer.
- Re-test against current whoosh3 before deep triage — writer context managers
  now release the lock on exceptions.

## 6. Not a Whoosh issue — set aside
- Other backends: Elasticsearch, Solr, Xapian, PostgreSQL FTS.
- Pure Haystack-layer bugs: `SearchQuerySet` result caching, pagination,
  templates, `SimpleLazyObject`.

## Output of a review
For each issue, leave (or record) one of:
- **Config answer** — point to the analyzer/query/scoring recipe above.
- **Needs repro** — ask for a minimal example against current whoosh3.
- **Closable** — behavior is fixed/changed in whoosh3 (note the version).
- **Not Whoosh** — route to the correct backend or Haystack layer.


## Worked example
> *"Searching for `e-mail` returns nothing, but `email` works."*

1. Different backend? No — reporter shows a Whoosh index.
2. Haystack construct? No — it's about matching.
3. Indexed-vs-matched? **Yes** → bucket 2 (query parsing / reserved chars).

Answer: the `-` is being treated as a query operator (or stripped by the
backend's `clean()`), so `e-mail` parses as `e AND NOT mail`. Fixes: search the
raw term as a phrase, or index a keyword/non-stemmed field so `e-mail` survives
tokenization. Outcome: **Config answer**, no code change in Haystack.

## Suggested labels for routing
Applying consistent labels makes a second review pass much faster:

| Bucket | Label | Typical resolution |
| --- | --- | --- |
| 1 Analysis | `whoosh/analysis` | Config answer |
| 2 Query parsing | `whoosh/query` | Config answer / needs repro |
| 3 Scoring | `whoosh/scoring` | Config answer |
| 4 Performance | `whoosh/perf` | Needs repro against whoosh3 |
| 5 Locking | `whoosh/concurrency` | Retest on whoosh3 |
| 6 Not Whoosh | `backend/<name>` or `haystack-core` | Route / close |
| 7 Old issue or stale | `needs review` | Route / close |
