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

## 1. Analysis / tokenization
Symptoms: unexpected stemming, accented characters not matching, CJK/non-English
tokenization, n-gram sizing, field-name collisions.

- Whoosh analyzers are **composable and per-field**
  (`Tokenizer | Filter | Filter`), so most of these are configuration, not bugs.
- Stemming surprises (e.g. `Sodenthaler → sodenthal`) → the field should let the
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
