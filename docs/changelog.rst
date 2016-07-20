Changelog
=========

%%version%% (unreleased)
------------------------

New
~~~

- SearchQuerySet.set_spelling_query for custom spellcheck. [Chris Adams]

  This makes it much easier to customize the text sent to the
  backend search engine for spelling suggestions independently
  from the actual query being executed.

- Support ManyToManyFields in model_attr lookups. [Arjen Verstoep]

  Thanks to @Terr for the patch

- `update_index` will retry after backend failures. [Gilad Beeri]

  Now `update_index` will retry failures multiple times before aborting
  with a progressive time delay.

  Thanks to Gilad Beeri (@giladbeeri) for the patch

- `highlight()` accepts custom values on Solr and ES. [Chris Adams]

  This allows the default values to be overriden and arbitrary
  backend-specific parameters may be provided to Solr or ElasticSearch.

  Thanks to Tim Babych (@tymofij) for the patch

  Closes #1334

- Allow Routers to return multiple indexes. [Chris Adams]

  Thanks to Hugo Chargois (@hchargois) for the patch

  Closes #1337
  Closes #934

- Support for newer versions of Whoosh. [Chris Adams]

- Split SearchView.create_response into get_context. [Chris Adams]

  This makes it easy to override the default `create_response` behaviour
  if you don't want a standard HTML response.

  Thanks @seocam for the patch

  Closes #1338

- Django 1.9 support thanks to Claude Paroz. [Chris Adams]

- Create a changelog using gitchangelog. [Chris Adams]

  This uses `gitchangelog <https://github.com/vaab/gitchangelog>`_ to
  generate docs/changelog.rst from our Git commit history using the tags
  for each version. The configuration is currently tracking upstream
  exactly except for our version tags being prefixed with "v".

Changes
~~~~~~~

- Support for Solr 5+ spelling suggestion format. [Chris Adams]

- Set install requirements for Django versions. [Chris Adams]

  This will prevent accidentally breaking apps when Django 1.10 is
  released.

  Closes #1375

- Avoid double-query for queries matching no results. [Chris Adams]

- Update supported/tested Django versions. [Chris Adams]

  * setup.py install_requires uses `>=1.8` to match our current test
    matrix
  * Travis allows failures for Django 1.10 so we can start tracking the
    upcoming release

- Make backend subclassing easier. [Chris Adams]

  This change allows the backend build_search_kwargs to
  accept arbitrary extra arguments, making life easier for authors of `SearchQuery` or `SearchBackend` subclasses when they can directly pass a value which is directly supported by the backend search client.

- Update_index logging & multiprocessing improvements. [Chris Adams]

  * Since older versions of Python are no longer supported we no
    longer conditionally import multiprocessing (see #1001)
  * Use multiprocessing.log_to_stderr for all messages
  * Remove previously-disabled use of the multiprocessing workers for index removals, allowing the worker code to be simplified

- Moved signal processor loading to app_config.ready. [Chris Adams]

  Thanks to @claudep for the patch

  Closes #1260

- Handle `__in=[]` gracefully on Solr. [Chris Adams]

  This commit avoids the need to check whether a list is empty to avoid an
  error when using it for an `__in` filter.

  Closes #358
  Closes #1311

Fix
~~~

- Tests will fall back to the Apache archive server. [Chris Adams]

  The Apache 4.10.4 release was quietly removed from the mirrors without a
  redirect. Until we have time to add newer Solr releases to the test
  suite we'll download from the archive and let the Travis build cache
  store it.

- Whoosh backend support for RAM_STORE (closes #1386) [Martin Owens]

  Thanks to @doctormo for the patch

- Unsafe update_worker multiprocessing sessions. [Chris Adams]

  The `update_index` management command does not handle the
  `multiprocessing` environment safely. On POSIX systems,
  `multiprocessing` uses `fork()` which means that when called in a
  context such as the test suite where the connection has already been
  used some backends like pysolr or ElasticSearch may have an option
  socket connected to the search server and that leaves a potential race
  condition where HTTP requests are interleaved, producing unexpected
  errors.

  This commit resets the backend connection inside the workers and has
  been stable across hundreds of runs, unlike the current situation where
  a single-digit number of runs would almost certainly have at least one
  failure.

  Other improvements:
  * Improved sanity checks for indexed documents in management
    command test suite. This wasn’t actually the cause of the
    problem above but since I wrote it while tracking down the
    real problem there’s no reason not to use it.
  * update_index now checks that each block dispatched was
    executed to catch any possible silent failures.

  Closes #1376
  See #1001

- Tests support PyPy. [Chris Adams]

  PyPy has an optimization which causes it to call __len__ when running a
  list comprehension, which is the same thing Python does for
  `list(iterable)`. This commit simply changes the test code to always use
  `list` the PyPy behaviour matches CPython.

- Avoid an extra query on empty spelling suggestions. [Chris Adams]

  None was being used as a placeholder to test whether to run
  a spelling suggestion query but was also a possible response
  when the backend didn’t return a suggestion, which meant
  that calling `spelling_suggestion()` could run a duplicate
  query.

- MultiValueField issues with single value (#1364) [Arjen Verstoep]

  Thanks to @terr for the patch!

- Queryset slicing and reduced code duplication. [Craig de Stigter]

  Now pagination will not lazy-load all earlier pages before returning the
  result.

  Thanks to @craigds for the patch

  Closes #1269
  Closes #960

- Handle negative timestamps returned from ES. [Chris Adams]

  Elastic search can return negative timestamps for histograms if the
  dates are pre-1970. This PR properly handles these pre-1970 dates.

  Thanks to @speedplane for the patch

  Closes #1239

- SearchMixin allows form initial values. [Chris Adams]

  Thanks to @ahoho for the patch

  Closes #1319

- Graceful handling of empty __in= lists on ElasticSearch. [Chris Adams]

  Thanks to @boulderdave for the ES version of #1311

  Closes #1335

Other
~~~~~

- Merge pull request #1349 from sbussetti/master. [Chris Adams]

  Fix logging call in `update_index`

- Fixes improper call to logger in mgmt command. [sbussetti]

- Merge pull request #1340 from claudep/manage_commands. [Chris Adams]

  chg: migrate management commands to argparse

- Updated management commands from optparse to argparse. [Claude Paroz]

  This follows Django's same move and prevents deprecation warnings.
  Thanks Mario César for the initial patch.

- Merge pull request #1225 from gregplaysguitar/patch-1. [Chris Adams]

  fix: correct docstring for ModelSearchForm.get_models !minor

- Fix bogus docstring. [Greg Brown]

- Merge pull request #1328 from claudep/travis19. [Chris Adams]

  Updated test configs to include Django 1.9

- Updated test configs to include Django 1.9. [Claude Paroz]

- Merge pull request #1313 from chrisbrooke/Fix-elasticsearch-2.0-meta-
  data-changes. [Chris Adams]

- Remove boost which is now unsupported. [Chris Brooke]

- Fix concurrency issues when building UnifiedIndex. [Chris Adams]

  We were getting this error a lot when under load in a multithreaded wsgi
  environment:

      Model '%s' has more than one 'SearchIndex`` handling it.

  Turns out the connections in haystack.connections and the UnifiedIndex
  instance were stored globally. However there is a race condition in
  UnifiedIndex.build() when multiple threads both build() at once,
  resulting in the above error.

  Best fix is to never share the same engine or UnifiedIndex across
  multiple threads. This commit does that.

  Closes #959
  Closes #615

- Load connection routers lazily. [Chris Adams]

  Thanks to Tadas Dailyda (@skirsdeda) for the patch

  Closes #1034
  Closes #1296

- DateField/DateTimeField accept strings values. [Chris Adams]

  Now the convert method will be called by default when string values are
  received instead of the normal date/datetime values.

  Closes #1188

- Fix doc ReST warning. [Chris Adams]

- Merge pull request #1297 from martinsvoboda/patch-1. [Sam Peka]

  Highlight elasticsearch 2.X is not supported yet

- Highlight in docs that elasticsearch 2.x is not supported yet. [Martin
  Svoboda]

- Start updating compatibility notes. [Chris Adams]

  * Deprecate versions of Django which are no longer
    supported by the Django project team
  * Update ElasticSearch compatibility messages
  * Update Travis / Tox support matrix

- Merge pull request #1287 from ses4j/patch-1. [Sam Peka]

  Remove duplicated SITE_ID from test_haystack/settings.py

- Remove redundant SITE_ID which was duplicated twice. [Scott Stafford]

- Add ``fuzzy`` operator to SearchQuerySet. [Chris Adams]

  This exposes the backends’ native fuzzy query support.

  Thanks to Ana Carolina (@anacarolinats) and Steve Bussetti (@sbussetti)
  for the patch.

- Merge pull request #1281 from itbabu/python35. [Justin Caratzas]

  Add python 3.5 to tests

- Add python 3.5 to tests. [Marco Badan]

  ref: https://docs.djangoproject.com/en/1.9/faq/install/#what-python-version-can-i-use-with-django

- SearchQuerySet: don’t trigger backend access in __repr__ [Chris Adams]

  This can lead to confusing errors or performance issues by
  triggering backend access at unexpected locations such as
  logging.

  Closes #1278

- Merge pull request #1276 from mariocesar/patch-1. [Chris Adams]

  Use compatible get_model util to support new django versions

  Thanks to @mariocesar for the patch!

- Reuse haystack custom get model method. [Mario César Señoranis Ayala]

- Removed unused import. [Mario César Señoranis Ayala]

- Use compatible get_model util to support new django versions. [Mario
  César Señoranis Ayala]

- Merge pull request #1263 from dkarchmer/patch-1. [Chris Adams]

  Update views_and_forms.rst

- Update views_and_forms.rst. [David Karchmer]

  After breaking my head for an hour, I realized the instructions to upgrade to class based views is incorrect. It should indicate that switch from `page` to `page_obj` and not `page_object`

v2.3.2 (2015-11-11)
-------------------

- V2.3.2 maintenance update. [Chris Adams]

- Fix #1253. [choco]

- V2.3.2 pre-release version bump. [Chris Adams]

- Allow individual records to be skipped while indexing. [Chris Adams]

  Previously there was no easy way to skip specific objects other than
  filtering the queryset. This change allows a prepare method to raise
  `SkipDocument` after calling methods or making other checks which cannot
  easily be expressed as database filters.

  Thanks to Felipe Prenholato (@chronossc) for the patch

  Closes #380
  Closes #1191

v2.4.1 (2015-10-29)
-------------------

- V2.4.1. [Chris Adams]

- Minimal changes to the example project to allow test use. [Chris
  Adams]

- Merge remote-tracking branch 'django-haystack/pr/1261' [Chris Adams]

  The commit in #1252 / #1251 was based on the assumption that the
  tutorial used the new generic views, which is not yet correct.

  This closes #1261 by restoring the wording and adding some tests to
  avoid regressions in the future before the tutorial is overhauled.

- Rename 'page_obj' with 'page' in the tutorial, section Search Template
  as there is no 'page_obj' in the controller and this results giving
  'No results found' in the search. [bboneva]

- Style cleanup. [Chris Adams]

  * Remove duplicate & unused imports
  * PEP-8 indentation & whitespace
  * Use `foo not in bar` instead of `not foo in bar`

- Update backend logging style. [Chris Adams]

  * Make Whoosh message consistent with the other backends
  * Pass exception info to loggers in except: blocks
  * PEP-8

- Avoid unsafe default value on backend clear() methods. [Chris Adams]

  Having a mutable structure like a list as a default value is unsafe;
  this commit changes that to the standard None.

- Merge pull request #1254 from chocobn69/master. [Chris Adams]

  Update for API change in elasticsearch 1.8 (closes #1253)

  Thanks to @chocobn69 for the patch

- Fix #1253. [choco]

- Tests: update Solr launcher for changed mirror format. [Chris Adams]

  The Apache mirror-detection script appears to have changed its response
  format recently. This change handles that and makes future error
  messages more explanatory.

- Bump doc version numbers - closes #1105. [Chris Adams]

- Merge pull request #1252 from rhemzo/master. [Chris Adams]

  Update tutorial.rst (closes #1251)

  Thanks to @rhemzo for the patch

- Update tutorial.rst. [rhemzo]

  change page for page_obj

- Merge pull request #1240 from speedplane/improve-cache-fill. [Chris
  Adams]

  Use a faster implementation of query result cache

- Use a faster implementation of this horrible cache. In my tests it
  runs much faster and uses far less memory. [speedplane]

- Merge pull request #1149 from lovmat/master. [Chris Adams]

  FacetedSearchMixin bugfixes and improvements

  * Updated documentation & example code
  * Fixed inheritance chain
  * Added facet_fields

  Thanks to @lovmat for the patch

- Updated documentation, facet_fields attribute. [lovmat]

- Added facet_fields attribute. [lovmat]

  Makes it easy to include facets into FacetedSearchVIew

- Bugfixes. [lovmat]

- Merge pull request #1232 from dlo/patch-1. [Chris Adams]

  Rename elasticsearch-py to elasticsearch in docs

  Thanks to @dlo for the patch

- Rename elasticsearch-py to elasticsearch in docs. [Dan Loewenherz]

- Update wording in SearchIndex get_model exception. [Chris Adams]

  Thanks to Greg Brown (@gregplaysguitar) for the patch

  Closes #1223

- Corrected exception wording. [Greg Brown]

- Allow failures on Python 2.6. [Chris Adams]

  Some of our test dependencies like Mock no longer support it. Pinning
  Mock==1.0.1 on Python 2.6 should avoid that failure but the days of
  Python 2.6 are clearly numbered.

- Travis: stop testing unsupported versions of Django on Python 2.6.
  [Chris Adams]

- Use Travis’ matrix support rather than tox. [Chris Adams]

  This avoids a layer of build setup and makes the Travis
  console reports more useful

- Tests: update the test version of Solr in use. [Chris Adams]

  4.7.2 has disappeared from most of the Apache mirrors

v2.4.0 (2015-06-09)
-------------------

- Release 2.4.0. [Chris Adams]

- Merge pull request #1208 from ShawnMilo/patch-1. [Chris Adams]

  Fix a typo in the faceting docs

- Possible typo fix. [Shawn Milochik]

  It seems that this was meant to be results.

- 2.4.0 release candidate 2. [Chris Adams]

- Fix Django 1.9 deprecation warnings. [Ilan Steemers]

  * replaced get_model with haystack_get_model which returns the right function depending on the Django version
  * get_haystack_models is now compliant with > Django 1.7

  Closes #1206

- Documentation: update minimum versions of Django, Python. [Chris
  Adams]

- V2.4.0 release candidate. [Chris Adams]

- Bump version to 2.4.0.dev1. [Chris Adams]

- Travis: remove Django 1.8 from allow_failures. [Chris Adams]

- Tests: update test object creation for Django 1.8. [Chris Adams]

  Several of the field tests previously assigned a related test model
  instance before saving it::

      mock_tag = MockTag(name='primary')
      mock = MockModel()
      mock.tag = mock_tag

  Django 1.8 now validates this dodgy practice and throws an error.

  This commit simply changes it to use `create()` so the mock_tag will
  have a pk before assignment.

- Update AUTHORS. [Chris Adams]

- Tests: fix deprecated Manager.get_query_set call. [Chris Adams]

- Updating haystack to test against django 1.8. [Chris Adams]

  Updated version of @troygrosfield's patch updating the test-runner for
  Django 1.8

  Closes #1175

- Travis: allow Django 1.8 failures until officially supported. [Chris
  Adams]

  See #1175

- Remove support for Django 1.5, add 1.8 to tox/travis. [Chris Adams]

  The Django project does not support 1.5 any more and it's the source of
  most of our false-positive test failures

- Use db.close_old_connections instead of close_connection. [Chris
  Adams]

  Django 1.8 removed the `db.close_connection` method.

  Thanks to Alfredo Armanini (@phingage) for the patch

- Fix mistake in calling super TestCase method. [Ben Spaulding]

  Oddly this caused no issue on Django <= 1.7, but it causes numerous
  errors on Django 1.8.

- Correct unittest imports from commit e37c1f3. [Ben Spaulding]

- Prefer stdlib unittest over Django's unittest2. [Ben Spaulding]

  There is no need to fallback to importing unittest2 because Django 1.5
  is the oldest Django we support, so django.utils.unittest is guaranteed
  to exist.

- Prefer stdlib OrderedDict over Django's SortedDict. [Ben Spaulding]

  The two are not exactly they same, but they are equivalent for
  Haystack's needs.

- Prefer stdlib importlib over Django's included version. [Ben
  Spaulding]

  The app_loading module had to shuffle things a bit. When it was
  importing the function it raised a [RuntimeError][]. Simply importing
  the module resolved that.

  [RuntimeError]: https://gist.github.com/benspaulding/f36eaf483573f8e5f777

- Docs: explain how field boosting interacts with filter. [Chris Adams]

  Thanks to @amjoconn for contributing a doc update to help newcomers

  Closes #1043

- Add tests for values/values_list slicing. [Chris Adams]

  This confirms that #1019 is fixed

- Update_index: avoid gaps in removal logic. [Chris Adams]

  The original logic did not account for the way removing records
  interfered with the pagination logic.

  Closes #1194

- Update_index: don't use workers to remove stale records. [Chris Adams]

  There was only minimal gain to this because, unlike indexing, removal is
  a simple bulk operation limited by the search engine.

  See #1194
  See #1201

- Remove lxml dependency. [Chris Adams]

  pysolr 3.3.2+ no longer requires lxml, which saves a significant install
  dependency

- Allow individual records to be skipped while indexing. [Chris Adams]

  Previously there was no easy way to skip specific objects other than
  filtering the queryset. This change allows a prepare method to raise
  `SkipDocument` after calling methods or making other checks which cannot
  easily be expressed as database filters.

  Thanks to Felipe Prenholato (@chronossc) for the patch

  Closes #380
  Closes #1191

- Update_index: avoid "MySQL has gone away error" with workers. [Eric
  Bressler (Platform)]

  This fixes an issue with a stale database connection being passed to
  a multiprocessing worker when using `--remove`

  Thanks to @ebressler for the patch

  Closes #1201

- Depend on pysolr 3.3.1. [Chris Adams]

- Start-solr-test-server: avoid Travis dependency. [Chris Adams]

  This will now fall back to the current directory when run outside of our Travis-CI environment

- Fix update_index --remove handling. [Chris Adams]

  * Fix support for custom keys by reusing the stored value rather than
    regenerating following the default pattern
  * Batch remove operations using the total number of records
    in the search index rather than the database

  Closes #1185
  Closes #1186
  Closes #1187

- Merge pull request #1177 from paulshannon/patch-1. [Chris Adams]

  Update TravisCI link in README

- Update TravisCI link. [Paul Shannon]

  I think the repo got changed at some point and the old project referenced at travisci doesn't exist anymore...

- Travis: enable containers. [Chris Adams]

  * Move apt-get installs to the addons/apt_packages:
    http://docs.travis-ci.com/user/apt-packages/
  * Set `sudo: false` to enable containers:
    http://docs.travis-ci.com/user/workers/container-based-infrastructure/

- Docs: correct stray GeoDjango doc link. [Chris Adams]

- Document: remove obsolete Whoosh Python 3 warning. [Chris Adams]

  Thanks to @gitaarik for the pull request

  Closes #1154
  Fixes #1108

- Remove method_decorator backport (closes #1155) [Chris Adams]

  This was no longer used anywhere in the Haystack source or documentation

- Travis: enable APT caching. [Chris Adams]

- Travis: update download caching. [Chris Adams]

- App_loading cleanup. [Chris Adams]

  * Add support for Django 1.7+ AppConfig
  * Rename internal app_loading functions to have haystack\_ prefix to make
    it immediately obvious that they are not Django utilities and start
  * Add tests to avoid regressions for apps nested with multiple levels of
    module hierarchy like `raven.contrib.django.raven_compat`
  * Refactor app_loading logic to make it easier to remove the legacy
    compatibility code when we eventually drop support for older versions
    of Django

  Fixes #1125
  Fixes #1150
  Fixes #1152
  Closes #1153

- Switch defaults closer to Python 3 defaults. [Chris Adams]

  * Add __future__ imports:

  isort --add_import 'from __future__ import absolute_import, division, print_function, unicode_literals'

  * Add source encoding declaration header

- Setup.py: use strict PEP-440 dev version. [Chris Adams]

  The previous version was valid as per PEP-440 but triggers a warning in
  pkg_resources

- Merge pull request #1146 from kamilmowinski/patch-1. [Chris Adams]

  Fix typo in SearchResult documentation

- Update searchresult_api.rst. [kamilmowinski]

- Merge pull request #1143 from wicol/master. [Chris Adams]

  Fix deprecation warnings in Django 1.6.X (thanks @wicol)

- Fix deprecation warnings in Django 1.6.X. [Wictor]

  Options.model_name was introduced in Django 1.6 together with a deprecation warning:
  https://github.com/django/django/commit/ec469ade2b04b94bfeb59fb0fc7d9300470be615

- Travis: move tox setup to before_script. [Chris Adams]

  This should cause dependency installation problems to show up as build
  errors rather than outright failures

- Update ElasticSearch defaults to allow autocompleting numbers. [Chris
  Adams]

  Previously the defaults for ElasticSearch used the `lowercase`
  tokenizer, which prevented numbers from being autocompleted.

  Thanks to Phill Tornroth (@phill-tornroth) for contributing a patch
  which changes the default settings to use the `standard` tokenizer
  with the `lowercase` filter

  Closes #1056

- Update documentation for new class-based views. [Chris Adams]

  Thanks to @troygrosfield for the pull-request

  Closes #1139
  Closes #1133
  See #1130

- Added documentation for configuring facet behaviour. [Chris Adams]

  Thanks to Philippe Luickx for the contribution

  Closes #1111

- UnifiedIndex has a stable interface to get all indexes. [Chris Adams]

  Previously it was possible for UnifiedIndexes.indexes to be empty when
  called before the list had been populated. This change deprecates
  accessing `.indexes` directly in favor of a `get_indexes()` accessor
  which will call `self.build()` first if necessary.

  Thanks to Phill Tornroth for the patch and tests.

  Closes #851

- Add support for SQ in SearchQuerySet.narrow() (closes #980) [Chris
  Adams]

  Thanks to Andrei Fokau (@andreif) for the patch and tests

- Disable multiprocessing on Python 2.6 (see #1001) [Chris Adams]

  multiprocessing.Pool.join() hangs reliably on Python 2.6 but
  not any later version tested. Since this is an optional
  feature we’ll simply disable it

- Bump version number to 2.4.0-dev. [Chris Adams]

- Update_index: wait for all pool workers to finish. [Chris Adams]

  There was a race condition where update_index() would return
  before all of the workers had finished updating Solr. This
  manifested itself most frequently as Travis failures
  for the multiprocessing test (see #1001).

- Tests: Fix ElasticSearch index setup (see #1093) [Chris Adams]

  Previously when clear_elasticsearch_index() was called to
  reset the tests, this could produce confusing results
  because it cleared the mappings without resetting the
  backend’s setup_complete status and thus fields which were
  expected to have a specific type would end up being inferred

  With this changed test_regression_proper_start_offsets and
  test_more_like_this no longer fail

- Update rebuild_index --nocommit handling and add tests. [Chris Adams]

  rebuild_index builds its option list by combining the options from
  clear_index and update_index. This previously had a manual exclude list
  for options which were present in both commands to avoid conflicts but
  the nocommit option wasn't in that list.

  This wasn't tested because our test suite uses call_command rather than
  invoking the option parser directly.

  This commit also adds tests to confirm that --nocommit will actually
  pass commit=False to clear_index and update_index.

  Closes #1140
  See #1090

- Support ElasticSearch 1.x distance filter syntax (closes #1003) [Chris
  Adams]

  The elasticsearch 1.0 release was backwards incompatible
  with our previous usage.

  Thanks to @dulaccc for the patch adding support.

- Docs: add Github style guide link to pull request instructions. [Chris
  Adams]

  The recent Github blog post makes a number of good points:

  https://github.com/blog/1943-how-to-write-the-perfect-pull-request

- Fixed exception message when resolving model_attr. [Wictor]

  This fixes the error message displayed when model_attr references an
  unknown attribute.

  Thanks to @wicol for the patch

  Closes #1094

- Compatibility with Django 1.7 app loader (see #1097) [Chris Adams]

  * Added wrapper around get_model, so that Django 1.7 uses the new app
    loading mechanism.
  * Added extra model check to prevent that a simple module is treated as
    model.

  Thanks to Dirk Eschler (@deschler) for the patch.

- Fix index_fieldname to match documentation (closes #825) [Chris Adams]

  @jarig contributed a fix to ensure that index_fieldname renaming does
  not interfere with using the field name declared on the index.

- Add tests for Solr/ES spatial order_by. [Chris Adams]

  This exists primarily to avoid the possibility of breaking
  compatibility with the inconsistent lat, lon ordering used
  by Django, Solr and ElasticSearch.

- Remove undocumented `order_by_distance` [Chris Adams]

  This path was an undocumented artifact of the original
  geospatial feature-branch back in the 1.X era. It wasn’t
  documented and is completely covered by the documented API.

- ElasticSearch tests: PEP-8 cleanup. [Chris Adams]

- Implement managers tests for spatial features. [Chris Adams]

  This is largely shadowed by the actual spatial tests but it
  avoids surprises on the query generation

  * Minor PEP-8

- Remove unreferenced add_spatial methods. [Chris Adams]

  SolrSearchQuery and ElasticsearchSearchQuery both defined
  an `add_spatial` method which was neither called nor
  documented.

- Remove legacy httplib/httplib2 references. [Chris Adams]

  We’ve actually delegated the actual work to requests but the
  docs & tests had stale references

- Tests: remove legacy spatial backend code. [Chris Adams]

  This has never run since the solr_native_distance backend
  did not exist and thus the check always failed silently

- ElasticSearch backend: minor PEP-8 cleanup. [Chris Adams]

- Get-solr-download-url: fix Python 3 import path. [Chris Adams]

  This allows the scripts to run on systems where Python 3 is
  the default version

- Merge pull request #1130 from troygrosfield/master. [Chris Adams]

  Added generic class based search views

  (thanks @troygrosfield)

- Removed "expectedFailure". [Troy Grosfield]

- Minor update. [Troy Grosfield]

- Added tests for the generic search view. [Troy Grosfield]

- Hopefully last fix for django version checking. [Troy Grosfield]

- Fix for django version check. [Troy Grosfield]

- Adding fix for previously test for django 1.7. [Troy Grosfield]

- Adding py34-django1.7 to travis. [Troy Grosfield]

- Test for the elasticsearch client. [Troy Grosfield]

- Added unicode_literals import for py 2/3 compat. [Troy Grosfield]

- Added generic class based search views. [Troy Grosfield]

- Merge pull request #1101 from iElectric/nothandledclass. [Chris Adams]

  Report correct class when raising NotHandled

- Report correct class when raising NotHandled. [Domen Kožar]

- Merge pull request #1090 from andrewschoen/feature/no-commit-flag.
  [Chris Adams]

  Adds a --nocommit arg to the update_index, clear_index and rebuild_index management command.

- Adds a --nocommit arg to the update_index, clear_index and
  rebuild_index management commands. [Andrew Schoen]

- Merge pull request #1103 from pkafei/master. [Chris Adams]

  Update documentation to reference Solr 4.x

- Changed link to official archive site. [Portia Burton]

- Added path to schema.xml. [Portia Burton]

- Added latest version of Solr to documentation example. [Portia Burton]

- Update ElasticSearch version requirements. [Chris Adams]

- Elasticsearch's python api by default has _source set to False, this
  causes keyerror mentioned in bug #1019. [xsamurai]

- Solr: clear() won’t call optimize when commit=False. [Chris Adams]

  An optimize will trigger a commit implicitly so we’ll avoid
  calling it when the user has requested not to commit

- Bumped __version__ (closes #1112) [Dan Watson]

- Travis: allow PyPy builds to fail. [Chris Adams]

  This is currently unstable and it's not a first-class supported platform
  yet

- Tests: fix Solr server tarball test. [Chris Adams]

  On a clean Travis instance, the tarball won't exist

- Tests: have Solr test server startup script purge corrupt tarballs.
  [Chris Adams]

  This avoids tests failing if a partial download is cached by Travis

- Merge pull request #1084 from streeter/admin-mixin. [Daniel Lindsley]

  Document and add an admin mixin

- Document support for searching in the Django admin. [Chris Streeter]

- Add some spacing. [Chris Streeter]

- Create an admin mixin for external use. [Chris Streeter]

  There are cases where one might have a different base admin class, and
  wants to use the search features in the admin as well. Creating a mixin
  makes this a bit cleaner.

v2.3.1 (2014-09-22)
-------------------

- V2.3.1. [Chris Adams]

- Tolerate non-importable apps like django-debug-toolbar. [Chris Adams]

  If your installed app isn't even a valid Python module, haystack will
  issue a warning but continue.

  Thanks to @gojomo for the patch

  Closes #1074
  Closes #1075

- Allow apps without models.py on Django <1.7. [Chris Adams]

  This wasn't officially supported by Django prior to 1.7 but is used by
  some third-party apps such as Grappelli

  This commit adds a somewhat contrived test app to avoid future
  regressions by ensuring that the test suite always has an application
  installed which does not have models.py

  See #1073

v2.3.0 (2014-09-19)
-------------------

- Travis: Enable IRC notifications. [Chris Adams]

- Fix app loading call signature. [Chris Adams]

  Updated code from #1016 to ensure that get_models always
  returns a list (previously on Django 1.7 it would return
  the bare model when called with an argument of the form
  `app.modelname`)

  Add some basic tests

- App loading: use ImproperlyConfigured for bogus app names. [Chris
  Adams]

  This never worked but we’ll be more consistent and return
  ImproperlyConfigured instead of a generic LookupError

- App Loading: don’t suppress app-registry related exceptions. [Chris
  Adams]

  This is just asking for trouble in the future. If someone comes up with
  an edge case, we should add a test for it

- Remove Django version pin from install_requires. [Chris Adams]

- Django 1.7 support for app discovery. [Chris Adams]

  * Refactored @Xaroth’s patch from #1015 into a separate utils
    module
  * PEP-8 cleanup

- Start the process of updating for v2.3 release. [Chris Adams]

- Django 1.7 compatibility for model loading. [Chris Adams]

  This refactors the previous use of model _meta.module_name and updates
  the tests so the previous change can be tested safely.

  Closes #981
  Closes #982

- Update tox Django version pins. [Chris Adams]

- Mark expected failures for Django 1.7 (see #1069) [Chris Adams]

- Django 1.7: ensure that the app registry is ready before tests are
  loaded. [Chris Adams]

  The remaining test failures are due to some of the oddities in model
  mocking, which can be solved by overhauling the way we do tests and
  mocks.

- Tests: Whoosh test overhaul. [Chris Adams]

  * Move repetitive filesystem reset logic into WhooshTestCase which
    cleans up after itself
  * Use mkdtemp instead of littering up the current directory with a
    'tmp' subdirectory
  * Use skipIf rather than expectFailure on test_writable to disable
    it only when STORAGE=ram rather than always

- Unpin elasticsearch library version for testing. [Chris Adams]

- Tests: add MIDDLEWARE_CLASSES for Django 1.7. [Chris Adams]

- Use get_model_ct_tuple to generate template name. [Chris Adams]

- Refactor simple_backend to use get_model_ct_tuple. [Chris Adams]

- Haystack admin: refactor to use get_model_ct_tuple. [Chris Adams]

- Consolidate model meta references to use get_model_ct (see #981)
  [Chris Adams]

  This use of a semi-public Django interface will break in Django 1.7
  and we can start preparing by using the existing
  haystack.utils.get_model_ct function instead of directly accessing
  it everywhere.

- Refactor get_model_ct to handle Django 1.7, add tuple version. [Chris
  Adams]

  We have a mix of model _meta access which usually expects strings but in
  a few places needs raw values. This change adds support for Django 1.7
  (see https://code.djangoproject.com/ticket/19689) and allows raw tuple
  access to handle other needs in the codebase

- Add Django 1.7 warning to Sphinx docs as well. [Chris Adams]

v2.2.1 (2014-09-03)
-------------------

- Mark 2.2.X as incompatible with Django 1.7. [Chris Adams]

- Tests: don't suppress Solr stderr logging. [Chris Adams]

  This will make easier to tell why Solr sometimes goes away on Travis

- Update Travis & Tox config. [Chris Adams]

  * Tox: wait for Solr to start before running tests
  * Travis: allow solr & pip downloads to be cached
  * Travis now uses start-solr-test-server.sh instead of travis-solr
  * Test Solr configuration uses port 9001 universally as per the
    documentation
  * Change start-solr-test-server.sh to change into its containing
    directory, which also allows us to remove the realpath dependency
  * Test Solr invocation matches pysolr
      * Use get-solr-download-url script to pick a faster mirror
      * Upgrade to Solr 4.7.2

- Travis, Tox: add Django 1.7 targets. [Chris Adams]

- Merge pull request #1055 from andreif/feature/realpath-fallback-osx.
  [Chris Adams]

- Fallback to pwd if realpath is not available. [Andrei Fokau]

- Merge pull request #1053 from gandalfar/patch-1. [Chris Adams]

- Update example for Faceting to reference page.object_list. [Jure
  Cuhalev]

  Instead of `results` - ref #1052

- Add PyPy targets to Tox & Travis. [Chris Adams]

  Closes #1049

- Merge pull request #1044 from areski/patch-1. [Chris Adams]

  Update Xapian install instructions (thanks @areski)

- Update Xapian install. [Areski Belaid]

- Docs: fix signal processors link in searchindex_api. [Chris Adams]

  Correct a typo in b676b17dbc4b29275a019417e7f19f531740f05e

- Merge pull request #1050 from jogwen/patch-2. [Chris Adams]

- Link to 'signal processors' [Joanna Paulger]

- Merge pull request #1047 from g3rd/patch-1. [Chris Adams]

  Update the installing search engine documentation URL (thanks @g3rd)

- Fixed the installing search engine doc URL. [Chad Shrock]

- Merge pull request #1025 from reinout/patch-1. [Chris Adams]

  Fixed typo in templatetag docs example (thanks to @reinout)

- Fixed typo in example. [Reinout van Rees]

  It should be `css_class` in the template tag example instead of just `class`. (It is mentioned correctly in the syntax line earlier).

v2.2.0 (2014-08-03)
-------------------

- Release v2.2.0. [Chris Adams]

- Test refactor - merge all the tests into one test suite (closes #951)
  [Chris Adams]

  Major refactor by @honzakral which stabilized the test suite, makes it easier to run and add new tests and
  somewhat faster, too.

  * Merged all the tests
  * Mark tests as skipped when a backend is not available (e.g. no ElasticSearch or Solr connection)
  * Massively simplified test runner (``python setup.py test``)

  Minor updates:

  * Travis:

    - Test Python 3.4
    - Use Solr 4.6.1

  * Simplified legacy test code which can now be replaced by the test utilities in newer versions of Django
  * Update ElasticSearch client & tests for ES 1.0+
  * Add option for SearchModelAdmin to specify the haystack connection to use
  * Fixed a bug with RelatedSearchQuerySet caching using multiple instances (429d234)

- RelatedSearchQuerySet: move class globals to instance properties.
  [Chris Adams]

  This caused obvious failures in the test suite and presumably
  elsewhere when multiple RelatedSearchQuerySet instances were in use

- Merge pull request #1032 from maikhoepfel/patch-1. [Justin Caratzas]

  Drop unused variable when post-processing results

- Drop unused variable when post-processing results. [Maik Hoepfel]

  original_results is not used in either method, and can be safely removed.

- 404 when initially retrieving mappings is ok. [Honza Král]

- Ignore 400 (index already exists) when creating an index in
  Elasticsearch. [Honza Král]

- ElasticSearch: update clear() for 1.x+ syntax. [Chris Adams]

  As per http://www.elasticsearch.org/guide/en/elasticsearch/reference/1.x/docs-delete-by-query.html this should be nested inside a
  top-level query block:

  {“query”: {“query_string”: …}}

- Add setup.cfg for common linters. [Chris Adams]

- ElasticSearch: avoid KeyError for empty spelling. [Chris Adams]

  It was possible to get a KeyError when spelling suggestions were
  requested but no suggestions are returned by the backend.

  Thanks to Steven Skoczen (@skoczen) for the patch

- Merge pull request #970 from tobych/patch-3. [Justin Caratzas]

  Improve punctuation in super-scary YMMV warning

- Improve punctuation in super-scary YMMV warning. [Toby Champion]

- Merge pull request #969 from tobych/patch-2. [Justin Caratzas]

  Fix typo; clarify purpose of search template

- Fix typo; clarify purpose of search template. [Toby Champion]

- Merge pull request #968 from tobych/patch-1. [Justin Caratzas]

  Fix possessive "its" in tutorial.rst

- Fix possessive "its" [Toby Champion]

- Merge pull request #938 from Mbosco/patch-1. [Daniel Lindsley]

  Update tutorial.rst

- Update tutorial.rst. [BoscoMW]

- Fix logging call in SQS post_process_results (see #648) [Chris Adams]

  This was used in an except: handler and would only be executed when a
  load_all() queryset retrieved a model which wasn't registered with the
  index.

- Merge pull request #946 from gkaplan/spatial-docs-fix. [Daniel
  Lindsley]

  Small docs fix for spatial search example code

- Fix typo with instantiating Distance units. [Graham Kaplan]

- Solr backend: correct usage of pysolr delete. [Chris Adams]

  We use HAYSTACK_ID_FIELD in other places but the value passed to
  pysolr's delete() method must use the keyword argument ``id``:

  https://github.com/toastdriven/pysolr/blob/v3.1.0/pysolr.py#L756

  Although the value is passed to Solr an XML tag named ``<id>`` it will
  always be checked against the actual ``uniqueKey`` field even if it uses
  a custom name:

  https://wiki.apache.org/solr/UpdateXmlMessages#A.22delete.22_documents_by_ID_and_by_Query

  Closes #943

- Add a note on elasticsearch-py versioning with regards to 1.0. [Honza
  Král]

- Ignore 404 when removing a document from elasticsearch. [Honza Král]

  Fixes #942

- Ignore missing index during .clear() [Honza Král]

  404 in indices.delete can only mean that the index is there, no issue
  for a delete operation

  Fixes #647

- Tests: remove legacy targets. [Chris Adams]

  * Django 1.4 is no longer supported as per the documentation
  * Travis: use Python 3.3 targets instead of 3.2

- Tests: update pysolr requirement to 3.1.1. [Chris Adams]

  3.1.1 shipped a fix for a change in the Solr response format for the
  content extraction handler

- Merge pull request #888 from acdha/888-solr-field-list-regression.
  [Chris Adams]

  Solr / ElasticSearch backends: restore run() kwargs handling

  This fixes an earlier regression which did not break functionality but made `.values()` and `.values_list()` much less of an optimization than intended.

  #925 will be a more comprehensive refactor but this is enough of a performance win to be worth including if a point release happens before #925 lands.

- ElasticSearch backend: run() kwargs are passed directly to search
  backend. [Chris Adams]

  This allows customization by subclasses and also fixes #888
  by ensuring that the custom field list prepared by
  `ValuesQuerySet` and `ValuesListQuerySet` is actually used.

- Solr backend: run() kwargs are passed directly to search backend.
  [Chris Adams]

  This allows customization by subclasses and also fixes #888
  by ensuring that the custom field list prepared by
  `ValuesQuerySet` and `ValuesListQuerySet` is actually used.

- Tests: skip Solr content extraction with old PySolr. [Chris Adams]

  Until pysolr 3.1.1 ships there's no point in running the Solr content
  extraction tests because they'll fail:

  https://github.com/toastdriven/pysolr/pull/104

- Make sure DJANGO_CT and DJANGO_ID fields are not analyzed. [Honza
  Král]

- No need to store fields separately in elasticsearch. [Honza Král]

  That will justlead to fields being stored once - as part of _source as
  well as in separate index that would never be used by haystack (would be
  used only in special cases when requesting just that field, which can
  be, with minimal overhead, still just extracted from the _source as it
  is).

- Remove extra code. [Honza Král]

- Simplify mappings for elasticsearch fields. [Honza Král]

  - don't specify defaults (index:analyzed for strings, boost: 1.0)
  - omit extra settings that have little or negative effects
    (term_vector:with_positions_offsets)
  - only use type-specific settings (not_analyzed makes no sense for
    non-string types)

  Fixes #866

- Add narrow queries as individual subfilter to promote caching. [Honza
  Král]

  Each narrow query will be cached individually which means more cache
  reuse

- Doc formatting fix. [Honza Král]

- Allow users to pass in additional kwargs to Solr and Elasticsearch
  backends. [Honza Král]

  Fixes #674, #862

- Whoosh: allow multiple order_by() fields. [Chris Adams]

  The Whoosh backend previously prevented the use of more than one
  order_by field. It now allows multiple fields as long as every field
  uses the same sort direction.

  Thanks to @qris, @overflow for the patch

  Closes #627
  Closes #919

- Fix bounding box calculation for spatial queries (closes #718) [Chris
  Adams]

  Thanks @jasisz for the fix

- Docs: fix ReST syntax error in searchqueryset_api.rst. [Chris Adams]

- Tests: update test_more_like_this for Solr 4.6. [Chris Adams]

- Tests: update test_quotes_regression exception test. [Chris Adams]

  This was previously relying on the assumption that a query would not
  match, which is Solr version dependent, rather than simply
  confirming that no exception is raised

- Tests: update Solr schema to match current build_solr_schema. [Chris
  Adams]

  * Added fields used in spatial tests: location, username, comment
  * Updated schema for recent Solr
  * Ran `xmllint --c14n "$*" | xmllint --format --encode "utf-8" -`

- Tests: update requirements to match tox. [Chris Adams]

- Move test Solr instructions into a script. [Chris Adams]

  These will just rot horribly if they're not actually executed on a
  regular basis…

- Merge pull request #907 from gam-phon/patch-1. [Chris Adams]

- Fix url for solr 3.5.0. [Yaser Alraddadi]

- Merge pull request #775 from stefanw/avoid-pks-seen-on-update. [Justin
  Caratzas]

  Avoid unnecessary, potentially huge db query on index update

- Merge branch 'master' into avoid-pks-seen-on-update. [Stefan
  Wehrmeyer]

  Change smart_text into smart_bytes as in master

  Conflicts:
  	haystack/management/commands/update_index.py

- Upgraded python3 in tox to 3.3. [justin caratzas]

  3.3 is a better target for haystack than 3.2, due to PEP414

- Merge pull request #885 from HonzaKral/elasticsearch-py. [Justin
  Caratzas]

  Use elasticsearch-py instead of pyelasticsearch.

- Use elasticsearch-py instead of pyelasticsearch. [Honza Král]

  elasticsearch-py is the official Python client for Elasticsearch.

- Merge pull request #899 from acdha/html5-input-type=search. [Justin
  Caratzas]

  Search form <input type="search">

- Use HTML5 <input type=search> (closes #899) [Chris Adams]

- Update travis config so that unit tests will run with latest solr +
  elasticsearch. [justin caratzas]

- Merge remote-tracking branch 'HonzaKral/filtered_queries' Fixes #886.
  [Daniel Lindsley]

- Use terms filter for DJANGO_CT, *much* faster. [Honza Král]

- Cleaner query composition when it comes to filters in ES. [Honza Král]

- Fixed typo in AUTHORS. [justin caratzas]

- Added pabluk to AUTHORS. [Pablo SEMINARIO]

- Fixed ValueError exception when SILENTLY_FAIL=True. [Pablo SEMINARIO]

- Merge pull request #882 from benspaulding/docs/issue-607. [Justin
  Caratzas]

  Remove bit about SearchQuerySet.load_all_queryset deprecation

- Remove bit about SearchQuerySet.load_all_queryset deprecation. [Ben
  Spaulding]

  That method was entirely removed in commit b8048dc0e9e3.

  Closes #607. Thanks to @bradleyayers for the report.

- Merge pull request #881 from benspaulding/docs/issue-606. [Justin
  Caratzas]

  Fix documentation regarding ModelSearchIndex to match current behavior

- Fix documentation regarding ModelSearchIndex to match current
  behavior. [Ben Spaulding]

  Closes #606. Thanks to @bradleyayers for the report.

- Fixed #575 & #838, where a change in Whoosh 2.5> required explicitly
  setting the Searcher.search() limit to None to restore correct
  results. [Keryn Knight]

  Thanks to scenable and Shige Abe (typeshige) for
  the initial reports, and to scenable for finding
  the root issue in Whoosh.

- Removed python 1.4 / python 3.2 tox env because thats not possible.
  [justin caratzas]

  also pinned versions of requirements for testing

- Added test for autocomplete whitespace fix. [justin caratzas]

- Fixed autocomplete() method: spaces in query. [Ivan Virabyan]

- Fixed basepython for tox envs, thanks --showconfig. [justin caratzas]

  also, added latest django 1.4 release, which doesn't error out
  currently.

  Downgraded python3.3 to python3.2, as thats what the lastest debian
  stable includes.  I'm working on compiling pypy and python3.3 on the
  test box, so those will probably be re-added as time allows.

  failing tests: still solr context extraction + spatial

- Fixed simple backend for django 1.6, _fields was removed. [justin
  caratzas]

- [tox] run tests for 1.6, fix test modules so they are found by the new
  test runner. [justin caratzas]

  These changes are backwards-compatible with django 1.5.  As of this
  commit, the only failing tests are the Solr extractraction test, and the
  spatial tests.

- Switch solr configs to solr 4. [justin caratzas]

  almost all tests passing, but spatial not working

- Update solr schema template to fix stopwords_en.txt relocation.
  [Patrick Altman]

  Seems that in versions >3.6 and >4 stopwords_en.txt moved
  to a new location. This won't be backwards compatible for
  older versions of solr.

  Addresses issues #558, #560
  In addition, issue #671 references this problem

- Pass `using` to index_queryset for update. [bigjust]

- Update tox to test pypy, py26, py27, py33, django1.5 and django1.6.
  [bigjust]

  django 1.6 doesn't actually work yet, but there are other efforts to get that working

- Fixed my own spelling test case. How embarrassing. [Dan Watson]

- Added a spelling test case for ElasticSearch. [Dan Watson]

- More ElasticSearch test fixes. [Dan Watson]

- Added some faceting tests for ElasticSearch. [Dan Watson]

- Fixed ordering issues in the ElasticSearch tests. [Dan Watson]

- Merge remote-tracking branch 'infoxchange/fix-elasticsearch-index-
  settings-reset' [Daniel Lindsley]

- Test ensuring recreating the index does not remove the mapping.
  [Alexey Kotlyarov]

- Reset backend state when deleting index. [Alexey Kotlyarov]

  Reset setup_complete and existing_mapping when an index is
  deleted. This ensures create_index is called later to restore
  the settings properly.

- Use Django's copy of six. [Dan Watson]

- Merge pull request #847 from luisbarrueco/mgmtcmd-fix. [Dan Watson]

  Fixed an update_index bug when using multiple connections

- Fixed an update_index bug when using multiple connections. [Luis
  Barrueco]

- Fixed a missed raw_input call on Python 3. [Dan Watson]

- Merge pull request #840 from postatum/fix_issue_807. [Justin Caratzas]

  Fixed issue #807

- Fixed issue #807. [postatum]

- Merge pull request #837 from nicholasserra/signals-docs-fix. [Justin
  Caratzas]

  Tiny docs fix in signal_processors example code

- Tiny docs fix in signal_processors example code. [Nicholas Serra]

- Merge pull request #413 from phill-tornroth/patch-1. [Justin Caratzas]

- Silly little change, I know.. but I actually ran into a case where I
  accidentally passed a list of models in without \*ing them. When that
  happens, we get a string formatting exception (not all arguments were
  formatted) instead of the useful "that ain't a model, kid" business.
  [Phill Tornroth]

- Merge pull request #407 from bmihelac/patch-1. [Justin Caratzas]

  Fixed doc, ``query`` is context variable and not in request.

- Fixed doc, ``query`` is context variable and not in request.
  [bmihelac]

- Merge pull request #795 from
  davesque/update_excluded_indexes_error_message. [Justin Caratzas]

  Improve error message for duplicate index classes

- Improve error message for duplicate index classes. [David Sanders]

  To my knowledge, the 'HAYSTACK_EXCLUDED_INDEXES' setting is no longer
  used.

- Started the v2.1.1 work. [Daniel Lindsley]

- Avoid unnecessary db query on index update. [Stefan Wehrmeyer]

  pks_seen is only needed if objects are removed from
  index, so only compute it if necessary.
  Improve pks_seen to not build an intermediary list.

v2.1.0 (2013-07-28)
-------------------

- Bumped to v2.1.0! [Daniel Lindsley]

- Python 3 support is done, thanks to RevSys & the PSF! Updated
  requirements in the docs. [Daniel Lindsley]

- Added all the new additions to AUTHORS. [Daniel Lindsley]

- Merge branch 'py3' [Daniel Lindsley]

- Added Python 3 compatibility notes. [Daniel Lindsley]

- Whoosh mostly working under Python 3. See docs for details. [Daniel
  Lindsley]

- Backported things removed from Django 1.6. [Daniel Lindsley]

- Final core changes. [Daniel Lindsley]

- Solr tests all but passing under Py3. [Daniel Lindsley]

- Elasticsearch tests passing under Python 3. [Daniel Lindsley]

  Requires git master (ES 1.0.0 beta) to work properly when using suggestions.

- Overrides passing under Py3. [Daniel Lindsley]

- Simple backend ported & passing. [Daniel Lindsley]

- Whoosh all but fully working under Python 3. [Daniel Lindsley]

- Closer on porting ES. [Daniel Lindsley]

- Core tests mostly pass on Py 3. \o/ [Daniel Lindsley]

  What's left are 3 failures, all ordering issues, where the correct output is present, but ordering is different between Py2 / Py3.

- More porting to Py3. [Daniel Lindsley]

- Started porting to py3. [Daniel Lindsley]

- Merge pull request #821 from knightzero/patch-1. [Justin Caratzas]

  Update autocomplete.rst

- Update autocomplete.rst. [knightzero]

- Merge pull request #744 from trigger-corp/master. [Justin Caratzas]

  Allow for document boosting with elasticsearch

- Update the current elasticsearch boost test to also test document
  boosting. [Connor Dunn]

- Map boost field to _boost in elasticsearch. [Connor Dunn]

  Means that including a boost field in a document will cause document level boosting.

- Added ethurgood to AUTHORS. [Daniel Lindsley]

- Add test__to_python for elastisearch backend. [Eric Thurgood]

- Fix datetime instantiation in elasticsearch backend's _to_python.
  [Eric Thurgood]

- Merge pull request #810 from pabluk/minor-docs-fix. [Chris Adams]

  Updated description for TIMEOUT setting - thanks @pabluk

- Updated description for TIMEOUT setting. [Pablo SEMINARIO]

- Updated the backend support docs. Thanks to kezabelle & dimiro1 for
  the report! [Daniel Lindsley]

- Added haystack-rqueue to "Other Apps". [Daniel Lindsley]

- Updated README & index. [Daniel Lindsley]

- Added installation instructions. [bigjust]

- Merge pull request #556 from h3/master. [Justin Caratzas]

  Updated to 'xapian_backend.XapianEngine' docs & example

- Updated XapianEngine module path. [h3]

- Updated XapianEngine module path. [h3]

- Merge pull request #660 from seldon/master. [Justin Caratzas]

  Some minor docs fixes

- Fixed a few typos in docs. [Lorenzo Franceschini]

- Add Educreations to who uses Haystack. [bigjust]

- Merge pull request #692 from stephenpaulger/master. [Justin Caratzas]

  Change the README link to latest 1.2 release.

- Update README.rst. [Stephen Paulger]

  Update 1.2.6 link to 1.2.7

- Merge pull request #714 from miracle2k/patch-1. [Justin Caratzas]

  Note enabling INCLUDE_SPELLING requires a reindex.

- Note enabling INCLUDE_SPELLING requires a reindex. [Michael Elsdörfer]

- Unicode support in SimpleSearchQuery (closes #793) [slollo]

- Merge pull request #790 from andrewschoen/feature/haystack-identifier-
  module. [Andrew Schoen]

  Added a new setting, HAYSTACK_IDENTIFIER_METHOD, which will allow a cust...

- Added a new setting, ``HAYSTACK_IDENTIFIER_METHOD``, which will allow
  a custom method to be provided for ``haystack.utils.get_identifier``.
  [Schoen]

- Fixed an exception log message in elasticsearch backend, and added a
  loading test for elasticsearch. [Dan Watson]

- Changed exception log message in whoosh backend to use
  __class__.__name__ instead of just __name__ (closes #641) [Jeffrey
  Tratner]

- Further bumped the docs on installing engines. [Daniel Lindsley]

- Update docs/installing_search_engines.rst. [Tom Dyson]

  grammar, Elasticsearch version and formatting consistency fixes.

- Added GroundCity & Docket Alarm to the Who Uses docs. [Daniel
  Lindsley]

- Started the development on v2.0.1. [Daniel Lindsley]

v2.0.0 (2013-05-12)
-------------------

- Bumped to v2.0.0! [Daniel Lindsley]

- Changed how ``Raw`` inputs are handled. Thanks to kylemacfarlane for
  the (really good) report. [Daniel Lindsley]

- Added a (passing) test trying to verify #545. [Daniel Lindsley]

- Fixed a doc example on custom forms. Thanks to GrivIN and benspaulding
  for patches. [Daniel Lindsley]

- Added a reserved character for Solr (v4+ supports regexes). Thanks to
  RealBigB for the initial patch. [Daniel Lindsley]

- Merge branch 'master' of github.com:toastdriven/django-haystack.
  [Jannis Leidel]

- Fixed the stats tests. [Daniel Lindsley]

- Adding description of stats support to docs. [Ranjit Chacko]

- Adding support for stats queries in Solr. [Ranjit Chacko]

- Added tests for the previous kwargs patch. [Daniel Lindsley]

- Bug fix to allow object removal without a commit. [Madan Thangavelu]

- Do not refresh the index after it has been deleted. [Kevin Tran]

- Fixed naming of manager for consistency. [Jannis Leidel]

  - renamed `HaystackManager` to `SearchIndexManager`
  - renamed `get_query_set` to `get_search_queryset`

- Updated the docs on running tests. [Daniel Lindsley]

- Merge branch 'madan' [Daniel Lindsley]

- Fixed the case where index_name isn't available. [Daniel Lindsley]

- Fixing typo to allow manager to switch between different index_labels.
  [Madan Thangavelu]

- Haystack manager and tests. [Madan Thangavelu]

- Removing unwanted spaces. [Madan Thangavelu]

- Object query manager for searchindex. [Madan Thangavelu]

- Added requirements file for testing. [Daniel Lindsley]

- Added a unit test for #786. [Dan Watson]

- Fixed a bug when passing "using" to SearchQuerySet (closes #786).
  [Rohan Gupta]

- Ignore the env directory. [Daniel Lindsley]

- Allow for setuptools as well as distutils. [Daniel Lindsley]

- Merge pull request #785 from mattdeboard/dev-mailing-list. [Chris
  Adams]

  Add note directing users to django-haystack-dev mailing list.

- Add note directing users to django-haystack-dev mailing list. [Matt
  DeBoard]

- Spelling suggestions for ElasticSearch (closes #769 and #747) [Dan
  Watson]

- Added support for sending facet options to the backend (closes #753)
  [Dan Watson]

- More_like_this: honor .models() restriction. [Chris Adams]

  Original patch by @mattdeboard updated to remove test drift since it was
  originally submitted

  Closes #593
  Closes #543

- Removed commercial support info. [Daniel Lindsley]

- Merge pull request #779 from pombredanne/pep386_docfixes. [Jannis
  Leidel]

  Update version to 2.0.0b0 in doc conf

- Update version to 2.0.0b0 in doc conf .. to redeem myself of the
  unlucky #777 minimess. [pombredanne]

- Merge pull request #778 from falinsky/patch-1. [Justin Caratzas]

  Fix bug in setup.py

- Fix bug. [Sergey Falinsky]

- Merge pull request #777 from pombredanne/patch-1. [Justin Caratzas]

  Update version to be a PEP386 strict with a minor qualifier of 0 for now...

- Update version to be a PEP386 strict with a minor qualifier of 0 for
  now. [pombredanne]

  This version becomes a "strict" version under PEP386 and should be recognized by install/packaging tools (such as distribute/distutils/setuptools) as newer than 2.0.0-beta. This will also help making small increments of the version which brings some sanity when using an update from HEAD and ensure that things will upgrade alright.

- Update_index: display Unicode model names (closes #767) [Chris Adams]

  The model's verbose_name_plural value is included as Unicode but under
  Python 2.x the progress message it was included in was a regular
  byte-string. Now it's correctly handled as Unicode throughout.

- Merge pull request #731 from adityar7/master. [Jannis Leidel]

  Setup custom routers before settings up signal processor.

- Setup custom routers before settings up signal processor. [Aditya
  Rajgarhia]

  Fixes https://github.com/toastdriven/django-haystack/issues/727

- Port the `from_python` method from pyelasticsearch to the
  Elasticsearch backend, similar to `to_python` in
  181bbc2c010a135b536e4d1f7a1c5ae4c63e33db. [Jannis Leidel]

  Fixes #762. Refs #759.

- Merge pull request #761 from stefanw/simple-models-filter. [Justin
  Caratzas]

  Make models filter work on simple backend

- Make model filter for simple backend work. [Stefan Wehrmeyer]

  Adds Stefan Wehrmeyer to AUTHORS for patch

- Merge pull request #746 from lazerscience/fix-update-index-output.
  [Justin Caratzas]

  Using force_text for indexing message

- Replacing `force_text` with `force_unicode`. #746. [Bernhard Vallant]

- Using force_text for indexing message. [Bernhard Vallant]

  verbose_name_plural may be a functional proxy object from ugettext_lazy,
  it should be forced to be a string!

- Support pyelasticsearch 0.4 change (closes #759) [Chris Adams]

  pyelasticsearch 0.4 removed the `to_python` method Haystack used.

  Thanks to @erikrose for the quick patch

- Merge pull request #755 from toastdriven/issue/754-doc-build-warning.
  [Chris Adams]

- Add preceding dots to hyperlink target; fixes issue 754. [Ben
  Spaulding]

  This error was introduced in commit faacbcb.

- Merge pull request #752 from bigjust/master. [Justin Caratzas]

  Fix Simple Score field collision

- Simple: Fix bug in score field collision. [bigjust]

  Previous commit 0a9c919 broke the simple backend for models that
  didn't have an indexed score field.  Added a test to cover regression.

- Set zip_safe in setup.py to prevent egg creation. [Jannis Leidel]

  This is a work around for a bug in Django that prevents detection of management commands embedded in packages installed as setuptools eggs.

- Merge pull request #740 from acdha/simplify-search-view-name-property.
  [Chris Adams]

  Remove redundant __name__ assignment on SearchView

- Remove redundant __name__ assignment on SearchView. [Chris Adams]

  __name__ was being explicitly set to a value which was the same as the
  default value.

  Additionally corrected the obsolete __name__ method declaration in the
  documentation which reflected the code prior to SHA:89d8096 in 2010.

- Merge pull request #698 from gjb83/master. [Chris Adams]

  Fixed deprecation warning for url imports on Django 1.3

  Thanks to @gjb83 for the patch.

- Removed star imports. [gjb83]

- Maintain Django 1.3 compatibility. [gjb83]

- Fixed deprecation warning. [gjb83]

  django.conf.urls.defaults is now deprecated. Use django.conf.urls instead.

- Merge pull request #743 from bigjust/solr-managementcmd-fix. [Justin
  Caratzas]

  Solr build_solr_schema: fixed a bug in build_solr_schema. Thanks to mjum...

- Solr build_solr_schema: fixed a bug in build_solr_schema. Thanks to
  mjumbewu for the report! [Justin Caratzas]

  If you tried to run build_solr_schema with a backend that supports
  schema building, but was not Solr (like Whoosh), then you would get an
  invalid schema.  This fix raises the ImproperlyConfigured exception
  with a proper message.

- Merge pull request #742 from bigjust/simple-backend-score-fix. [Justin
  Caratzas]

- Simple: removed conflicting score field from raw result objects.
  [Justin Caratzas]

  This keeps consistency with the Solr backend, which resolves this conflict
  in the same manner.

- ElasticSearch: fix AltParser test. [Chris Adams]

  AltParser queries are still broken but that fucntionality has only been
  listed as supported on Solr.

- Better Solr AltParser quoting (closes #730) [Chris Adams]

  Previously the Solr AltParser implementation embedded the search term as an
  attribte inside the {!…} construct, which required it to be doubly escaped.

  This change contributed by @ivirabyan moves the value outside the query,
  requiring only our normal quoting:

      q=(_query_:"{!edismax}Assassin's Creed")

  instead of:

      q=(_query_:"{!edismax v='Assassin's Creed'}")

  Thanks @ivirabyan for the patch!

- Solr: use nested query syntax for AltParser queries. [Chris Adams]

  The previous implementation would, given a query like this::

      sqs.filter(content=AltParser('dismax', 'library', qf="title^2 text" mm=1))

  generate a query like this::

      {!dismax v=library qf="title^2 text" mm=1}

  This works in certain situations but causes Solr to choke while parsing it
  when Haystack wraps this term in parentheses::

      org.apache.lucene.queryParser.ParseException: Cannot parse '({!dismax mm=1 qf='title^2 text institution^0.8' v=library})':
      Encountered " &lt;RANGEEX_GOOP&gt; "qf=\'title^1.25 "" at line 1, column 16.

  The solution is to use the nested query syntax described here:

      http://searchhub.org/2009/03/31/nested-queries-in-solr/

  This will produce a query like this, which works with Solr 3.6.2::

      (_query_:"{!edismax mm=1 qf='title^1.5 text institution^0.5' v=library}")

  Leaving the actual URL query string looking like this::

      q=%28_query_%3A%22%7B%21edismax+mm%3D1+qf%3D%27title%5E1.5+text+institution%5E0.5%27+v%3Dlibrary%7D%22%29

  * Tests updated for the new query generation output
  * A Solr backend task was added to actually run the dismax queries and verify
    that we're not getting Solr 400s errors due to syntax gremlins

- Pass active backend to index queryset calls (closes #534) [Chris
  Adams]

  Now the Index index_queryset() and read_queryset() methods will be called with
  the active backend name so they can optionally perform backend-specific
  filtering.

  This is extremely useful when using something like Solr cores to maintain
  language specific backends, allowing an Index to select the appropriate
  documents for each language::

      def index_queryset(self, using=None):
          return Post.objects.filter(language=using)

  Changes:
      * clear_index, update_index and rebuild_index all default to processing
        *every* backend. ``--using`` may now be provided multiple times to select
        a subset of the configured backends.
      * Added examples to the Multiple Index documentation page

- Because Windows. [Daniel Lindsley]

- Fixed the docs on debugging to cover v2. Thanks to eltesttox for the
  report. [Daniel Lindsley]

- That second colon matters. [Daniel Lindsley]

- Further docs on autocomplete. [Daniel Lindsley]

- Fixed the imports that would stomp on each other. [Daniel Lindsley]

  Thanks to codeinthehole, Attorney-Fee & imacleod for pointing this out.

- BACKWARD-INCOMPATIBLE: Removed ``RealTimeSearchIndex`` in favor of
  ``SignalProcessors``. [Daniel Lindsley]

  This only affects people who were using ``RealTimeSearchIndex`` (or a
  queuing variant) to perform near real-time updates. Those users should
  refer to the Migration documentation.

- Updated ignores. [Daniel Lindsley]

- Merge pull request #552 from hadesgames/master. [Jannis Leidel]

  Fixes process leak when using update_index with workers.

- Fixed update_index process leak. [Tache Alexandru]

- Merge branch 'master' of github.com:toastdriven/django-haystack.
  [Jannis Leidel]

- Merge pull request #682 from acdha/682-update_index-tz-support. [Chris
  Adams]

  update_index should use non-naive datetime when settings.USE_TZ=True

- Tests for update_index timezone support. [Chris Adams]

  * Confirm that update_index --age uses the Django timezone-aware now
    support function
  * Skip this test on Django 1.3

- Update_index: use tz-aware datetime where applicable. [Chris Adams]

  This will allow Django 1.4 users with USE_TZ=True to use update_index with time
  windowing as expected - otherwise the timezone offset needs to be manually
  included in the value passed to -a

- Tests: mark expected failures in Whoosh suite. [Chris Adams]

  This avoids making it painful to run the test suite and flags the tests which
  need attention

- Tests: mark expected failures in ElasticSearch suite. [Chris Adams]

  This avoids making it painful to run the test suite and flags the tests which
  need attention

- Multiple index tests: correct handling of Whoosh teardown. [Chris
  Adams]

  We can't remove the Whoosh directory per-test - only after every
  test has run…

- Whoosh tests: use a unique tempdir. [Chris Adams]

  This ensures that there's no way for results to persist across runs
  and lets the OS clean up the mess if we fail catastrophically

  The multiindex and regular whoosh tests will have different prefixes to ease
  debugging

- Merge pull request #699 from acdha/tox-multiple-django-versions.
  [Chris Adams]

  Minor tox.ini & test runner tidying

- Test runner: set exit codes on failure. [Chris Adams]

- Tox: refactor envlist to include Django versions. [Chris Adams]

  * Expanded base dependencies
  * Set TEST_RUNNER_ARGS=-v0 to reduce console noise
  * Add permutations of python 2.5, 2.6, 2.7 and django 1.3 and 1.4

- Test runner: add $TEST_RUNNER_ARGS env. variable. [Chris Adams]

  This allows you to export TEST_RUNNER_ARGS=-v0 to affect all 9
  invocations

- Tox: store downloads in tmpdir. [Chris Adams]

- Be a bit more careful when resetting connections in the
  multiprocessing updater. Fixes #562. [Jannis Leidel]

- Fixed distance handling in result parser of the elasticsearch backend.
  This is basically the second part of #566. Thanks to Josh Drake for
  the initial patch. [Jannis Leidel]

- Merge pull request #670 from dhan88/master. [Jannis Leidel]

  Elasticsearch backend using incorrect coordinates for geo_bounding_box (within) filter

- Elasticsearch geo_bounding_box filter expects top_left (northwest) and
  bottom_right (southeast). Haystack's elasticsearch backend is passing
  northeast and southwest coordinates instead. [Danny Han]

- Merge pull request #666 from caioariede/master. [Jannis Leidel]

  Fixes incorrect call to put_mapping on ElasticSearch backend

- Fixes incorrect call to put_mapping on elasticsearch backend. [Caio
  Ariede]

- Added ericholscher to AUTHORS. [Daniel Lindsley]

- Add a title for the support matrix so it's linkable. [Eric Holscher]

- Tests: command-line help and coverage.py support. [Chris Adams]

  This makes run_all_tests.sh a little easier to use and simplifies the process of
  running under coverage.py

  Closes #683

- Tests: basic help and coverage.py support. [Chris Adams]

  run_all_tests.sh now supports --help and --with-coverage

- Add a CONTRIBUTING.md file for Github. [Chris Adams]

  This is a migrated copy of docs/contributing.rst so Github can suggest it when
  pull requests are being created

- Fix combination logic for complex queries. [Chris Adams]

  Previously combining querysets which used a mix of logical AND and OR operations
  behaved unexpectedly.

  Thanks to @mjl for the patch and tests in SHA: 9192dbd

  Closes #613, #617

- Added rz to AUTHORS. [Daniel Lindsley]

- Fixed string joining bug in the simple backend. [Rodrigo Guzman]

- Added failing test case for #438. [Daniel Lindsley]

- Fix Solr more-like-this tests (closes #655) [Chris Adams]

  * Refactored the MLT tests to be less brittle in checking only
    the top 5 results without respect to slight ordering
    variations.
  * Refactored LiveSolrMoreLikeThisTestCase into multiple tests
  * Convert MLT templatetag tests to rely on mocks for stability
    and to avoid hard-coding backend assumptions, at the expense
    of relying completely on the backend MLT queryset-level tests
    to exercise that code.
  * Updated MLT code to always assume deferred querysets are
    available (introduced in Django 1.1) and removed a hard-coded
    internal attr check

- All backends: fixed more_like_this & deferreds. [Chris Adams]

  Django removed the get_proxied_model helper function in the 1.3 dev
  cycle:

  https://code.djangoproject.com/ticket/17678

  This change adds support for the simple new property access used by 1.3+

  BACKWARD INCOMPATIBLE: Django 1.2 is no longer supported

- Updated elasticsearch backend to use a newer pyelasticsearch release
  that features an improved API , connection pooling and better
  exception handling. [Jannis Leidel]

- Added Gidsy to list of who uses Haystack. [Jannis Leidel]

- Increased the number of terms facets returned by the Elasticsearch
  backend to 100 from the default 10 to work around an issue upstream.
  [Jannis Leidel]

  This is hopefully only temporary until it's fixed in Elasticsearch, see https://github.com/elasticsearch/elasticsearch/issues/1776.

- Merge pull request #643 from stephenmcd/master. [Chris Adams]

  Fixed logging in simple_backend

- Fixed logging in simple_backend. [Stephen McDonald]

- Added Pitchup to Who Uses. [Daniel Lindsley]

- Merge branch 'unittest2-fix' [Chris Adams]

- Better unittest2 detection. [Chris Adams]

  This supports Python 2.6 and earlier by shifting the import to look
  towards the future name rather than the past

- Merge pull request #652 from acdha/solr-content-extraction-test-fix.
  [Chris Adams]

  Fix the Solr content extraction handler tests

- Add a minimal .travis.yml file to suppress build spam. [Chris Adams]

  Until the travis-config branch is merged in, this can be spread around to avoid
  wasting time running builds before we're ready

- Tests: enable Solr content extraction handler. [Chris Adams]

  This is needed for the test_content_extraction test to pass

- Tests: Solr: fail immediately on config errors. [Chris Adams]

- Solr tests: clean unused imports. [Chris Adams]

- Suppress console DeprecationWarnings. [Chris Adams]

- Merge pull request #651 from acdha/unittest2-fix. [Chris Adams]

  Update unittest2 import logic so the tests can actually be run

- Update unittest2 import logic. [Chris Adams]

  We'll try to get it from Django 1.3+ but Django 1.2 users will need to install
  it manually

- Merge pull request #650 from bigjust/patch-1. [Chris Adams]

  Fix typo in docstring

- Fix typo. [Justin Caratzas]

- Refactor to use a dummy logger that lets you turn off logging. [Travis
  Swicegood]

- A bunch of Solr testing cleanup. [Chris Adams]

- Skip test is pysolr isn't available. [Travis Swicegood]

- Updated Who Uses to correct a backend usage. [Daniel Lindsley]

- Updated documentation about using the main pyelasticsearch release.
  [Jannis Leidel]

- Merge pull request #628 from kjoconnor/patch-1. [Jannis Leidel]

  Missing `

- Missing ` [Kevin O'Connor]

- Fixed a mostly-empty warning in the ``SearchQuerySet`` docs. Thanks to
  originell for the report! [Daniel Lindsley]

- Fixed the "Who Uses" entry on AstroBin. [Daniel Lindsley]

- Use the match_all query to speed up performing filter only queries
  dramatically. [Jannis Leidel]

- Fixed typo in docs. Closes #612. [Jannis Leidel]

- Updated link to celery-haystack repository. [Jannis Leidel]

- Fixed the docstring of SearchQuerySet.none. Closes #435. [Jannis
  Leidel]

- Fixed the way quoting is done in the Whoosh backend when using the
  ``__in`` filter. [Jason Kraus]

- Added the solrconfig.xml I use for testing. [Daniel Lindsley]

- Fixed typo in input types docs. Closes #551. [Jannis Leidel]

- Make sure an search engine's backend isn't instantiated on every call
  to the backend but only once. Fixes #580. [Jannis Leidel]

- Restored sorting to ES backend that was broken in
  d1fa95529553ef8d053308159ae4efc455e0183f. [Jannis Leidel]

- Prevent spatial filters from stomping on existing filters in
  ElasticSearch backend. [Josh Drake]

- Merge branch 'mattdeboard-sq-run-refactor' [Jannis Leidel]

- Fixed an ES test that seems like a change in behavior in recent ES
  versions. [Jannis Leidel]

- Merge branch 'sq-run-refactor' of https://github.com/mattdeboard
  /django-haystack into mattdeboard-sq-run-refactor. [Jannis Leidel]

- Refactor Solr & ES SearchQuery subclasses to use the ``build_params``
  from ``BaseSearchQuery`` to build the kwargs to be passed to the
  search engine. [Matt DeBoard]

  This refactor is made to make extending Haystack simpler. I only ran the Solr tests which invoked a ``run`` call (via ``get_results``), and those passed. I did not run the ElasticSearch tests; however, the ``run`` method for both Lucene-based search engines were identical before, and are identical now. The test I did run -- ``LiveSolrSearchQueryTestCase.test_log_query`` -- passed.

- Merge branch 'master' of https://github.com/toastdriven/django-
  haystack. [Jannis Leidel]

- Merge pull request #568 from duncm/master. [Jannis Leidel]

  Fix exception in SearchIndex.get_model()

- Fixed ``SearchIndex.get_model()`` to raise exception instead of
  returning it. [Duncan Maitland]

- Merge branch 'master' of https://github.com/toastdriven/django-
  haystack. [Jannis Leidel]

- Fixed Django 1.4 compatibility. Thanks to bloodchild for the report!
  [Daniel Lindsley]

- Refactored ``SearchBackend.search`` so that kwarg-generation
  operations are in a discrete method. [Matt DeBoard]

  This makes it much simpler to subclass ``SearchBackend`` (& the engine-specific variants) to add support for new parameters.

- Added witten to AUTHORS. [Daniel Lindsley]

- Fix for #378: Highlighter returns unexpected results if one term is
  found within another. [dan]

- Removed jezdez's old entry in AUTHORS. [Daniel Lindsley]

- Added Jannis to Primary Authors. [Daniel Lindsley]

- Merge branch 'master' of github.com:jezdez/django-haystack. [Jannis
  Leidel]

- Fixed a raise condition when using the simple backend (e.g. in tests)
  and changing the DEBUG setting dynamically (e.g. in integration
  tests). [Jannis Leidel]

- Add missing `ImproperlyConfigured` import from django's exceptions.
  [Luis Nell]

  l178 failed.

- Commercial support is now officially available for Haystack. [Daniel
  Lindsley]

- Using multiple workers (and resetting the connection) causes things to
  break when the app is finished and it moves to the next and does
  qs.count() to get a count of the objects in that app to index with
  psycopg2 reporting a closed connection. Manually closing the
  connection before each iteration if using multiple workers before
  building the queryset fixes this issue. [Adam Fast]

- Removed code leftover from v1.X. Thanks to kossovics for the report!
  [Daniel Lindsley]

- Fixed a raise condition when using the simple backend (e.g. in tests)
  and changing the DEBUG setting dynamically (e.g. in integration
  tests). [Jannis Leidel]

- All backends let individual documents fail, rather than failing whole
  chunks. Forward port of acdha's work on 1.2.X. [Daniel Lindsley]

- Added ikks to AUTHORS. [Daniel Lindsley]

- Fixed ``model_choices`` to use ``smart_unicode``. [Igor Támara]

- +localwiki.org. [Philip Neustrom]

- Added Pix Populi to "Who Uses". [Daniel Lindsley]

- Added contribution guidelines. [Daniel Lindsley]

- Updated the docs to reflect the supported version of Django. Thanks to
  catalanojuan for the original patch! [Daniel Lindsley]

- Fix PYTHONPATH Export and add Elasticsearch example. [Craig Nagy]

- Updated the Whoosh URL. Thanks to cbess for the original patch!
  [Daniel Lindsley]

- Reset database connections on each process on update_index when using
  --workers. [Diego Búrigo Zacarão]

- Moved the ``build_queryset`` method to ``SearchIndex``. [Alex Vidal]

  This method is used to build the queryset for indexing operations. It is copied
  from the build_queryset function that lived in the update_index management
  command.

  Making this change allows developers to modify the queryset used for indexing
  even when a date filter is necessary. See `tests/core/indexes.py` for tests.

- Fixed a bug where ``Indexable`` could be mistakenly recognized as a
  discoverable class. Thanks to twoolie for the original patch! [Daniel
  Lindsley]

- Fixed a bug with query construction. Thanks to dstufft for the report!
  [Daniel Lindsley]

  This goes back to erroring on the side of too many parens, where there weren't enough before. The engines will no-op them when they're not important.

- Fixed a bug where South would cause Haystack to setup too soon. Thanks
  to adamfast for the report! [Daniel Lindsley]

- Added Crate.io to "Who Uses"! [Daniel Lindsley]

- Fixed a small typo in spatial docs. [Frank Wiles]

- Logging: avoid forcing string interpolation. [Chris Adams]

- Fixed docs on using a template for Solr schema. [Daniel Lindsley]

- Add note to 'Installing Search Engines' doc explaining how to override
  the template used by 'build_solr_schema' [Matt DeBoard]

- Better handling of ``.models``. Thanks to zbyte64 for the report &
  HonzaKral for the original patch! [Daniel Lindsley]

- Added Honza to AUTHORS. [Daniel Lindsley]

- Handle sorting for ElasticSearch better. [Honza Kral]

- Update docs/backend_support.rst. [Issac Kelly]

- Fixed a bug where it's possible to erroneously try to get spelling
  suggestions. Thanks to bigjust for the report! [Daniel Lindsley]

- The ``dateutil`` requirement is now optional. Thanks to arthurnn for
  the report. [Daniel Lindsley]

- Fixed docs on Solr spelling suggestion until the new Suggester support
  can be added. Thanks to zw0rk & many others for the report! [Daniel
  Lindsley]

- Bumped to beta. [Daniel Lindsley]

  We're not there yet, but we're getting close.

- Added saved-search to subproject docs. [Daniel Lindsley]

- Search index discovery no longer swallows errors with reckless
  abandon. Thanks to denplis for the report! [Daniel Lindsley]

- Elasticsearch backend officially supported. [Daniel Lindsley]

  All tests passing.

- Back down to 3 on latest pyelasticsearch. [Daniel Lindsley]

- And then there were 3 (Elasticsearch test failures). [Daniel Lindsley]

- Solr tests now run faster. [Daniel Lindsley]

- Improved the tutorial docs. Thanks to denplis for the report! [Daniel
  Lindsley]

- Down to 9 failures on Elasticsearch. [Daniel Lindsley]

- Because the wishlist has changed. [Daniel Lindsley]

- A few small fixes. Thanks to robhudson for the report! [Daniel
  Lindsley]

- Added an experimental Elasticsearch backend. [Daniel Lindsley]

  Tests are not yet passing but it works in basic hand-testing. Passing test coverage coming soon.

- Fixed a bug related to the use of ``Exact``. [Daniel Lindsley]

- Removed accidental indent. [Daniel Lindsley]

- Ensure that importing fields without the GeoDjango kit doesn't cause
  an error. Thanks to dimamoroz for the report! [Daniel Lindsley]

- Added the ability to reload a connection. [Daniel Lindsley]

- Fixed ``rebuild_index`` to properly have all options available.
  [Daniel Lindsley]

- Fixed a bug in pagination. Thanks to sgoll for the report! [Daniel
  Lindsley]

- Added an example to the docs on what to put in ``INSTALLED_APPS``.
  Thanks to Dan Krol for the suggestion. [Daniel Lindsley]

- Changed imports so the geospatial modules are only imported as needed.
  [Dan Loewenherz]

- Better excluded index detection. [Daniel Lindsley]

- Fixed a couple of small typos. [Sean Bleier]

- Made sure the toolbar templates are included in the source
  distribution. [Jannis Leidel]

- Fixed a few documentation issues. [Jannis Leidel]

- Moved my contribution for the geospatial backend to a attribution of
  Gidsy which funded my work. [Jannis Leidel]

- Small docs fix. [Daniel Lindsley]

- Added input types, which enables advanced querying support. Thanks to
  CMGdigital for funding the development! [Daniel Lindsley]

- Added geospatial search support! [Daniel Lindsley]

  I have anxiously waited to add this feature for almost 3 years now.
  Support is finally present in more than one backend & I was
  generously given some paid time to work on implementing this.

  Thanks go out to:

    * CMGdigital, who paid for ~50% of the development of this feature
      & were awesomely supportive.
    * Jannis Leidel (jezdez), who did the original version of this
      patch & was an excellent sounding board.
    * Adam Fast, for patiently holding my hand through some of the
      geospatial confusions & for helping me verify GeoDjango
      functionality.
    * Justin Bronn, for the great work he originally did on
      GeoDjango, which served as a point of reference/inspiration
      on the API.

  And thanks to all others who have submitted a variety of
  patches/pull requests/interest throughout the years trying to get
  this feature in place.

- Added .values() / .values_list() methods, for fetching less data.
  Thanks to acdha for the original implementation! [Daniel Lindsley]

- Reduced the number of queries Haystack has to perform in many cases
  (pagination/facet_counts/spelling_suggestions). Thanks to acdha for
  the improvements! [Daniel Lindsley]

- Spruced up the layout on the new DjDT panel. [Daniel Lindsley]

- Fixed compatibility with Django pre-1.4 trunk. * The
  MAX_SHOW_ALL_ALLOWED variable is no longer available, and hence causes
  an ImportError with Django versions higher 1.3. * The
  "list_max_show_all" attribute on the ChangeList object is used
  instead. * This patch maintains compatibility with Django 1.3 and
  lower by trying to import the MAX_SHOW_ALL_ALLOWED variable first.
  [Aram Dulyan]

- Updated ``setup.py`` for the new panel bits. [Daniel Lindsley]

- Added a basic DjDT panel for Haystack. Thanks to robhudson for
  planting the seed that Haystack should bundle this! [Daniel Lindsley]

- Added the ability to specify apps or individual models to
  ``update_index``. Thanks to CMGdigital for funding this development!
  [Daniel Lindsley]

- Added ``--start/--end`` flags to ``update_index`` to allow finer-
  grained control over date ranges. Thanks to CMGdigital for funding
  this development! [Daniel Lindsley]

- I hate Python packaging. [Daniel Lindsley]

- Made ``SearchIndex`` classes thread-safe. Thanks to craigds for the
  report & original patch. [Daniel Lindsley]

- Added a couple more uses. [Daniel Lindsley]

- Bumped reqs in docs for content extraction bits. [Daniel Lindsley]

- Added a long description for PyPI. [Daniel Lindsley]

- Solr backend support for rich-content extraction. [Chris Adams]

  This allows indexes to use text extracted from binary files as well
  as normal database content.

- Fixed errant ``self.log``. [Daniel Lindsley]

  Thanks to terryh for the report!

- Fixed a bug with index inheritance. [Daniel Lindsley]

  Fields would seem to not obey the MRO while method did. Thanks to ironfroggy for the report!

- Fixed a long-time bug where the Whoosh backend didn't have a ``log``
  attribute. [Daniel Lindsley]

- Fixed a bug with Whoosh's edge n-gram support to be consistent with
  the implementation in the other engines. [Daniel Lindsley]

- Added celery-haystack to Other Apps. [Daniel Lindsley]

- Changed ``auto_query`` so it can be run on other, non-``content``
  fields. [Daniel Lindsley]

- Removed extra loops through the field list for a slight performance
  gain. [Daniel Lindsley]

- Moved ``EXCLUDED_INDEXES`` to a per-backend setting. [Daniel Lindsley]

- BACKWARD-INCOMPATIBLE: The default filter is now ``__contains`` (in
  place of ``__exact``). [Daniel Lindsley]

  If you were relying on this behavior before, simply add ``__exact`` to the fieldname.

- BACKWARD-INCOMPATIBLE: All "concrete" ``SearchIndex`` classes must now
  mixin ``indexes.Indexable`` as well in order to be included in the
  index. [Daniel Lindsley]

- Added tox to the mix. [Daniel Lindsley]

- Allow for less configuration. Thanks to jeromer & cyberdelia for the
  reports! [Daniel Lindsley]

- Fixed up the management commands to show the right alias & use the
  default better. Thanks to jeromer for the report! [Daniel Lindsley]

- Fixed a bug where signals wouldn't get setup properly, especially on
  ``RealTimeSearchIndex``. Thanks to byoungb for the report! [Daniel
  Lindsley]

- Fixed formatting in the tutorial. [Daniel Lindsley]

- Removed outdated warning about padding numeric fields. Thanks to
  mchaput for pointing this out! [Daniel Lindsley]

- Added a silent failure option to prevent Haystack from suppressing
  some failures. [Daniel Lindsley]

  This option defaults to ``True`` for compatibility & to prevent cases where lost connections can break reindexes/searches.

- Fixed the simple backend to not throw an exception when handed an
  ``SQ``. Thanks to diegobz for the report! [Daniel Lindsley]

- Whoosh now supports More Like This! Requires Whoosh 1.8.4. [Daniel
  Lindsley]

- Deprecated ``get_queryset`` & fixed how indexing happens. Thanks to
  Craig de Stigter & others for the report! [Daniel Lindsley]

- Fixed a bug where ``RealTimeSearchIndex`` was erroneously included in
  index discovery. Thanks to dedsm for the report & original patch!
  [Daniel Lindsley]

- Added Vickery to "Who Uses". [Daniel Lindsley]

- Require Whoosh 1.8.3+. It's for your own good. [Daniel Lindsley]

- Added multiprocessing support to ``update_index``! Thanks to
  CMGdigital for funding development of this feature. [Daniel Lindsley]

- Fixed a bug where ``set`` couldn't be used with ``__in``. Thanks to
  Kronuz for the report! [Daniel Lindsley]

- Added a ``DecimalField``. [Daniel Lindsley]

- Fixed a bug where a different style of import could confuse the
  collection of indexes. Thanks to groovecoder for the report. [Daniel
  Lindsley]

- Fixed a typo in the autocomplete docs. Thanks to anderso for the
  catch! [Daniel Lindsley]

- Fixed a backward-incompatible query syntax change Whoosh introduced
  between 1.6.1 & 1.6.2 that causes only one model to appear as though
  it is indexed. [Daniel Lindsley]

- Updated AUTHORS to reflect the Kent's involvement in multiple index
  support. [Daniel Lindsley]

- BACKWARD-INCOMPATIBLE: Added multiple index support to Haystack, which
  enables you to talk to more than one search engine in the same
  codebase. Thanks to: [Daniel Lindsley]

  * Kent Gormat for funding the development of this feature.
  * alex, freakboy3742 & all the others who contributed to Django's multidb feature, on which much of this was based.
  * acdha for inspiration & feedback.
  * dcramer for inspiration & feedback.
  * mcroydon for patch review & docs feedback.

  This commit starts the development efforts for Haystack v2.

v1.2.7 (2012-04-06)
-------------------

- Bumped to v1.2.7! [Daniel Lindsley]

- Solr: more informative logging when full_prepare fails during update.
  [Chris Adams]

  * Change the exception handler to record per-object failures
  * Log the precise object which failed in a manner which tools like Sentry can examine

- Added ikks to AUTHORS. [Daniel Lindsley]

- Fixed ``model_choices`` to use ``smart_unicode``. Thanks to ikks for
  the patch! [Daniel Lindsley]

- Fixed compatibility with Django pre-1.4 trunk. * The
  MAX_SHOW_ALL_ALLOWED variable is no longer available, and hence causes
  an ImportError with Django versions higher 1.3. * The
  "list_max_show_all" attribute on the ChangeList object is used
  instead. * This patch maintains compatibility with Django 1.3 and
  lower by trying to import the MAX_SHOW_ALL_ALLOWED variable first.
  [Aram Dulyan]

- Fixed a bug in pagination. Thanks to sgoll for the report! [Daniel
  Lindsley]

- Added an example to the docs on what to put in ``INSTALLED_APPS``.
  Thanks to Dan Krol for the suggestion. [Daniel Lindsley]

- Added .values() / .values_list() methods, for fetching less data.
  [Chris Adams]

- Reduced the number of queries Haystack has to perform in many cases
  (pagination/facet_counts/spelling_suggestions). [Chris Adams]

- Fixed compatibility with Django pre-1.4 trunk. * The
  MAX_SHOW_ALL_ALLOWED variable is no longer available, and hence causes
  an ImportError with Django versions higher 1.3. * The
  "list_max_show_all" attribute on the ChangeList object is used
  instead. * This patch maintains compatibility with Django 1.3 and
  lower by trying to import the MAX_SHOW_ALL_ALLOWED variable first.
  [Aram Dulyan]

v1.2.6 (2011-12-09)
-------------------

- I hate Python packaging. [Daniel Lindsley]

- Bumped to v1.2.6! [Daniel Lindsley]

- Made ``SearchIndex`` classes thread-safe. Thanks to craigds for the
  report & original patch. [Daniel Lindsley]

- Added a long description for PyPI. [Daniel Lindsley]

- Fixed errant ``self.log``. [Daniel Lindsley]

  Thanks to terryh for the report!

- Started 1.2.6. [Daniel Lindsley]

v1.2.5 (2011-09-14)
-------------------

- Bumped to v1.2.5! [Daniel Lindsley]

- Fixed a bug with index inheritance. [Daniel Lindsley]

  Fields would seem to not obey the MRO while method did. Thanks to ironfroggy for the report!

- Fixed a long-time bug where the Whoosh backend didn't have a ``log``
  attribute. [Daniel Lindsley]

- Fixed a bug with Whoosh's edge n-gram support to be consistent with
  the implementation in the other engines. [Daniel Lindsley]

- Added tswicegood to AUTHORS. [Daniel Lindsley]

- Fixed the ``clear_index`` management command to respect the ``--site``
  option. [Travis Swicegood]

- Removed outdated warning about padding numeric fields. Thanks to
  mchaput for pointing this out! [Daniel Lindsley]

- Added a silent failure option to prevent Haystack from suppressing
  some failures. [Daniel Lindsley]

  This option defaults to ``True`` for compatibility & to prevent cases where lost connections can break reindexes/searches.

- Fixed the simple backend to not throw an exception when handed an
  ``SQ``. Thanks to diegobz for the report! [Daniel Lindsley]

- Bumped version post-release. [Daniel Lindsley]

- Whoosh now supports More Like This! Requires Whoosh 1.8.4. [Daniel
  Lindsley]

v1.2.4 (2011-05-28)
-------------------

- Bumped to v1.2.4! [Daniel Lindsley]

- Fixed a bug where the old ``get_queryset`` wouldn't be used during
  ``update_index``. Thanks to Craig de Stigter & others for the report.
  [Daniel Lindsley]

- Bumped to v1.2.3! [Daniel Lindsley]

- Require Whoosh 1.8.3+. It's for your own good. [Daniel Lindsley]

v1.2.2 (2011-05-19)
-------------------

- Bumped to v1.2.2! [Daniel Lindsley]

- Added multiprocessing support to ``update_index``! Thanks to
  CMGdigital for funding development of this feature. [Daniel Lindsley]

- Fixed a bug where ``set`` couldn't be used with ``__in``. Thanks to
  Kronuz for the report! [Daniel Lindsley]

- Added a ``DecimalField``. [Daniel Lindsley]

v1.2.1 (2011-05-14)
-------------------

- Bumped to v1.2.1. [Daniel Lindsley]

- Fixed a typo in the autocomplete docs. Thanks to anderso for the
  catch! [Daniel Lindsley]

- Fixed a backward-incompatible query syntax change Whoosh introduced
  between 1.6.1 & 1.6.2 that causes only one model to appear as though
  it is indexed. [Daniel Lindsley]

v1.2.0 (2011-05-03)
-------------------

- V1.2.0! [Daniel Lindsley]

- Added ``request`` to the ``FacetedSearchView`` context. Thanks to
  dannercustommade for the report! [Daniel Lindsley]

- Fixed the docs on enabling spelling suggestion support in Solr.
  [Daniel Lindsley]

- Fixed a bug so that ``ValuesListQuerySet`` now works with the ``__in``
  filter. Thanks to jcdyer for the report! [Daniel Lindsley]

- Added the new ``SearchIndex.read_queryset`` bits. [Sam Cooke]

- Changed ``update_index`` so that it warns you if your
  ``SearchIndex.get_queryset`` returns an unusable object. [Daniel
  Lindsley]

- Removed Python 2.3 compat code & bumped requirements for the impending
  release. [Daniel Lindsley]

- Added treyhunner to AUTHORS. [Daniel Lindsley]

- Improved the way selected_facets are handled. [Chris Adams]

  * ``selected_facets`` may be provided multiple times.
  * Facet values are quoted to avoid backend confusion (i.e. `author:Joe Blow` is seen by Solr as `author:Joe AND Blow` rather than the expected `author:"Joe Blow"`)

- Add test for Whoosh field boost. [Trey Hunner]

- Enable field boosting with Whoosh backend. [Trey Hunner]

- Fixed the Solr & Whoosh backends to use the correct ``site`` when
  processing results. Thanks to Madan Thangavelu for the original patch!
  [Daniel Lindsley]

- Added lukeman to AUTHORS. [Daniel Lindsley]

- Updating Solr download and installation instructions to reference
  version 1.4.1 as 1.3.x is no longer available. Fixes #341. [lukeman]

- Revert "Shifted ``handle_registrations`` into ``models.py``." [Daniel
  Lindsley]

  This seems to be breaking for people, despite working here & passing tests. Back to the drawing board...

  This reverts commit 106758f88a9bc5ab7e505be62d385d876fbc52fe.

- Shifted ``handle_registrations`` into ``models.py``. [Daniel Lindsley]

  For historical reasons, it was (wrongly) kept & run in ``__init__.py``. This should help fix many people's issues with it running too soon.

- Pulled out ``EmptyResults`` for testing elsewhere. [Daniel Lindsley]

- Fixed a bug where boolean filtering wouldn't work properly on Whoosh.
  Thanks to alexrobbins for pointing it out! [Daniel Lindsley]

- Added link to 1.1 version of the docs. [Daniel Lindsley]

- Whoosh 1.8.1 compatibility. [Daniel Lindsley]

- Added TodasLasRecetas to "Who Uses". Thanks Javier! [Daniel Lindsley]

- Added a new method to ``SearchQuerySet`` to allow you to specify a
  custom ``result_class`` to use in place of ``SearchResult``. Thanks to
  aaronvanderlip for getting me thinking about this! [Daniel Lindsley]

- Added better autocomplete support to Haystack. [Daniel Lindsley]

- Changed ``SearchForm`` to be more permissive of missing form data,
  especially when the form is unbound. Thanks to cleifer for pointing
  this out! [Daniel Lindsley]

- Ensured that the primary key of the result is a string. Thanks to
  gremmie for pointing this out! [Daniel Lindsley]

- Fixed a typo in the tutorial. Thanks to JavierLopezMunoz for pointing
  this out! [Daniel Lindsley]

- Added appropriate warnings about ``HAYSTACK_<ENGINE>_PATH`` settings
  in the docs. [Daniel Lindsley]

- Added some checks for badly-behaved backends. [Daniel Lindsley]

- Ensure ``use_template`` can't be used with ``MultiValueField``.
  [Daniel Lindsley]

- Added n-gram fields for auto-complete style searching. [Daniel
  Lindsley]

- Added ``django-celery-haystack`` to the subapp docs. [Daniel Lindsley]

- Fixed the the faceting docs to correctly link to narrowed facets.
  Thanks to daveumr for pointing that out! [Daniel Lindsley]

- Updated docs to reflect the ``form_kwargs`` that can be used for
  customization. [Daniel Lindsley]

- Whoosh backend now explicitly closes searchers in an attempt to use
  fewer file handles. [Daniel Lindsley]

- Changed fields so that ``boost`` is now the parameter of choice over
  ``weight`` (though ``weight`` has been retained for backward
  compatibility). Thanks to many people for the report! [Daniel
  Lindsley]

- Bumped revision. [Daniel Lindsley]

v1.1 (2010-11-23)
-----------------

- Bumped version to v1.1! [Daniel Lindsley]

- The ``build_solr_schema`` command can now write directly to a file.
  Also includes tests for the new overrides. [Daniel Lindsley]

- Haystack's reserved field names are now configurable. [Daniel
  Lindsley]

- BACKWARD-INCOMPATIBLE: ``auto_query`` has changed so that only double
  quotes cause exact match searches. Thanks to craigds for the report!
  [Daniel Lindsley]

- Added docs on handling content-type specific output in results.
  [Daniel Lindsley]

- Added tests for ``content_type``. [Daniel Lindsley]

- Added docs on boosting. [Daniel Lindsley]

- Updated the ``searchfield_api`` docs. [Daniel Lindsley]

- ``template_name`` can be a list of templates passed to
  ``loader.select_template``. Thanks to zifot for the suggestion.
  [Daniel Lindsley]

- Moved handle_facet_parameters call into FacetField's __init__. [Travis
  Cline]

- Updated the pysolr dependency docs & added a debugging note about
  boost support. [Daniel Lindsley]

- Starting the beta. [Daniel Lindsley]

- Fixed a bug with ``FacetedSearchForm`` where ``cleaned_data`` may not
  exist. Thanks to imageinary for the report! [Daniel Lindsley]

- Added the ability to build epub versions of the docs. [Alfredo]

- Clarified that the current supported version of Whoosh is the 1.1.1+
  series. Thanks to glesica for the report & original patch! [Daniel
  Lindsley]

- The SearchAdmin now correctly uses SEARCH_VAR instead of assuming
  things. [Rob Hudson]

- Added the ability to "weight" individual fields to adjust their
  relevance. [David Sauve]

- Fixed facet fieldname lookups to use the proper fieldname. [Daniel
  Lindsley]

- Removed unneeded imports from the Solr backend. [Daniel Lindsley]

- Further revamping of faceting. Each field type now has a faceted
  variant that's created either with ``faceted=True`` or manual
  initialization. [Daniel Lindsley]

  This should also make user-created field types possible, as many of the gross ``isinstance`` checks were removed.

- Fixes SearchQuerySet not pickleable. Patch by oyiptong, tests by
  toastdriven. [oyiptong]

- Added the ability to remove objects from the index that are no longer
  in the database to the ``update_index`` management command. [Daniel
  Lindsley]

- Added a ``range`` filter type. Thanks to davisp & lukesneeringer for
  the suggestion! [Daniel Lindsley]

  Note that integer ranges are broken on the current Whoosh (1.1.1). However, date & character ranges seem to work fine.

- Consistency. [Daniel Lindsley]

- Ensured that multiple calls to ``count`` don't result in multiple
  queries. Thanks to Nagyman and others for the report! [Daniel
  Lindsley]

- Ensure that when fetching the length of a result set that the whole
  index isn't consumed (especially on Whoosh & Xapian). [Daniel
  Lindsley]

- Really fixed dict ordering bugs in SearchSite. [Travis Cline]

- Changed how you query for facets and how how they are presented in the
  facet counts.  Allows customization of facet field names in indexes.
  [Travis Cline]

  Lightly backward-incompatible (git only).

- Made it easier to override ``SearchView/SearchForm`` behavior when no
  query is present. [Daniel Lindsley]

  No longer do you need to override both ``SearchForm`` & ``SearchView`` if you want to return all results. Use the built-in ``SearchView``, provide your own custom ``SearchForm`` subclass & override the ``no_query_found`` method per the docstring.

- Don't assume that any pk castable to an integer should be an integer.
  [Carl Meyer]

- Fetching a list of all fields now produces correct results regardless
  of dict-ordering. Thanks to carljm & veselosky for the report! [Daniel
  Lindsley]

- Added notes about what is needed to make schema-building independent
  of dict-ordering. [Daniel Lindsley]

- Sorted model order matters. [Daniel Lindsley]

- Prevent Whoosh from erroring if the ``end_offset`` is less than or
  equal to 0. Thanks to zifot for the report! [Daniel Lindsley]

- Removed insecure use of ``eval`` from the Whoosh backend. Thanks to
  SmileyChris for pointing this out. [Daniel Lindsley]

- Disallow ``indexed=False`` on ``FacetFields``. Thanks to jefftriplett
  for the report! [Daniel Lindsley]

- Added ``FacetField`` & changed the way facets are processed. [Daniel
  Lindsley]

  Facet data is no longer quietly duplicated just before it goes into the index. Instead, full fields are created (with all the standard data & methods) to contain the faceted information.

  This change is backward-compatible, but allows for better extension, not requiring data duplication into an unfaceted field and a little less magic.

- EmptyQuerySet.facet_counts() won't hit the backend. [Chris Adams]

  This avoids an unnecessary extra backend query displaying the default
  faceted search form.

- TextMate fail. [Daniel Lindsley]

- Changed ``__name__`` to an attribute on ``SearchView`` to work with
  decorators. Thanks to trybik for the report! [Daniel Lindsley]

- Changed some wording on the tutorial to indicate where the data
  template should go. Thanks for the suggestion Davepar! [Daniel
  Lindsley]

- Merge branch 'whoosh-1.1' [Daniel Lindsley]

- Final cleanup before merging Whoosh 1.1 branch! [Daniel Lindsley]

- Final Whoosh 1.1.1 fixes. Waiting for an official release of Whoosh &
  hand testing, then this ought to be merge-able. [Daniel Lindsley]

- Upgraded the Whoosh backend to 1.1. Still one remaining test failure
  and two errors. Waiting on mchaput's thoughts/patches. [Daniel
  Lindsley]

- Mistakenly committed this change. This bug is not fixed. [Daniel
  Lindsley]

- Better handling of attempts at loading backends when the various
  supporting libraries aren't installed. Thanks to traviscline for the
  report. [Daniel Lindsley]

- Fixed random test failures from not running the Solr tests in awhile.
  [Daniel Lindsley]

- Changed mlt test to use a set comparison to eliminate failures due to
  ordering differences. [Travis Cline]

- Sped up Solr backend tests by moving away from RealTimeSearchIndex
  since it was adding objects to Solr when loading fixtures. [Travis
  Cline]

- Automatically add ``suggestion`` to the context if
  ``HAYSTACK_INCLUDE_SPELLING`` is set. Thanks to notanumber for the
  suggestion! [Daniel Lindsley]

- Added apollo13 to AUTHORS for the ``SearchForm.__init__`` cleanup.
  [Daniel Lindsley]

- Use kwargs.pop instead of try/except. [Florian Apolloner]

- Added Rob to AUTHORS for the admin cleanup. [Daniel Lindsley]

- Fixed selection_note text by adding missing zero. [Rob Hudson]

- Fixed full_result_count in admin search results. [Rob Hudson]

- Fixed admin actions in admin search results. [Rob Hudson]

- Added DevCheatSheet to "Who Uses". [Daniel Lindsley]

- Added Christchurch Art Gallery to "Who Uses". [Daniel Lindsley]

- Forgot to include ghostrocket as submitting a patch on the previous
  commit. [Daniel Lindsley]

- Fixed a serious bug in the ``simple`` backend that would flip the
  object instance and class. [Daniel Lindsley]

- Updated Whoosh to 0.3.18. [Daniel Lindsley]

- Updated NASA's use of Haystack in "Who Uses". [Daniel Lindsley]

- Changed how ``ModelSearchIndex`` introspects to accurately use
  ``IntegerField`` instead of ``FloatField`` as it was using. [Daniel
  Lindsley]

- Added CongresoVisible to Who Uses. [Daniel Lindsley]

- Added a test to verify a previous change to the ``simple`` backend.
  [Daniel Lindsley]

- Fixed the new admin bits to not explode on Django 1.1. [Daniel
  Lindsley]

- Added ``SearchModelAdmin``, which enables Haystack-based search within
  the admin. [Daniel Lindsley]

- Fixed a bug when not specifying a ``limit`` when using the
  ``more_like_this`` template tag. Thanks to symroe for the original
  patch. [Daniel Lindsley]

- Fixed the error messages that occur when looking up attributes on a
  model. Thanks to acdha for the patch. [Daniel Lindsley]

- Added pagination to the example search template in the docs so it's
  clear that it is supported. [Daniel Lindsley]

- Fixed copy-paste foul in ``Installing Search Engines`` docs. [Daniel
  Lindsley]

- Fixed the ``simple`` backend to return ``SearchResult`` instances, not
  just bare model instances. Thanks to Agos for the report. [Daniel
  Lindsley]

- Fixed the ``clear_index`` management command to respect
  ``--verbosity``. Thanks to kylemacfarlane for the report. [Daniel
  Lindsley]

- Altered the ``simple`` backend to only search textual fields. This
  makes the backend work consistently across all databases and is likely
  the desired behavior anyhow. Thanks to kylemacfarlane for the report.
  [Daniel Lindsley]

- Fixed a bug in the ``Highlighter`` which would double-highlight HTML
  tags. Thanks to EmilStenstrom for the original patch. [Daniel
  Lindsley]

- Updated management command docs to mention all options that are
  accepted. [Daniel Lindsley]

- Altered the Whoosh backend to correctly clear the index when using the
  ``RAMStorage`` backend. Thanks to kylemacfarlane for the initial
  patch. [Daniel Lindsley]

- Changed ``SearchView`` to allow more control over how many results are
  shown per page. Thanks to simonw for the suggestion. [Daniel Lindsley]

- Ignore ``.pyo`` files when listing out the backend options. Thanks to
  kylemacfarlane for the report. [Daniel Lindsley]

- Added CustomMade to Who Uses. [Daniel Lindsley]

- Moved a backend import to allow changing the backend Haystack uses on
  the fly. [Daniel Lindsley]

  Useful for testing.

- Added more debugging information to the docs. [Daniel Lindsley]

- Added DeliverGood.org to the "Who Uses" docs. [Daniel Lindsley]

- Added an settings override on ``HAYSTACK_LIMIT_TO_REGISTERED_MODELS``
  as a possible performance optimization. [Daniel Lindsley]

- Added the ability to pickle ``SearchResult`` objects. Thanks to dedsm
  for the original patch. [Daniel Lindsley]

- Added docs and fixed tests on the backend loading portions. Thanks to
  kylemacfarlane for the report. [Daniel Lindsley]

- Fixed bug with ``build_solr_schema`` where ``stored=False`` would be
  ignored. Thanks to johnthedebs for the report. [Daniel Lindsley]

- Added debugging notes for Solr. Thanks to smccully for reporting this.
  [Daniel Lindsley]

- Fixed several errors in the ``simple`` backend. Thanks to notanumber
  for the original patch. [Daniel Lindsley]

- Documentation fixes for Xapian. Thanks to notanumber for the edits!
  [Daniel Lindsley]

- Fixed a typo in the tutorial. Thanks to cmbeelby for pointing this
  out. [Daniel Lindsley]

- Fixed an error in the tutorial. Thanks to bencc for pointing this out.
  [Daniel Lindsley]

- Added a warning to the docs that ``SearchQuerySet.raw_search`` does
  not chain. Thanks to jacobstr for the report. [Daniel Lindsley]

- Fixed an error in the documentation on providing fields for faceting.
  Thanks to ghostmob for the report. [Daniel Lindsley]

- Fixed a bug where a field that's both nullable & faceted would error
  if no data was provided. Thanks to LarryEitel for the report. [Daniel
  Lindsley]

- Fixed a regression where the built-in Haystack fields would no longer
  facet correctly. Thanks to traviscline for the report. [Daniel
  Lindsley]

- Fixed last code snippet on the ``SearchIndex.prepare_FOO`` docs.
  Thanks to sk1p for pointing that out. [Daniel Lindsley]

- Fixed a bug where the schema could be built improperly if similar
  fieldnames had different options. [Daniel Lindsley]

- Added to existing tests to ensure that multiple faceted fields are
  included in the index. [Daniel Lindsley]

- Finally added a README. [Daniel Lindsley]

- Added a note about versions of the docs. [Daniel Lindsley]

- Go back to the default Sphinx theme. The custom Haystack theme is too
  much work and too little benefit. [Daniel Lindsley]

- Added a note in the tutorial about building the schema when using
  Solr. Thanks to trey0 for the report! [Daniel Lindsley]

- Fixed a bug where using ``SearchQuerySet.models()`` on an unregistered
  model would be silently ignored. [Daniel Lindsley]

  It is still silently ignored, but now emits a warning informing the user of why they may receive more results back than they expect.

- Added notes about the ``simple`` backend in the docs. Thanks to
  notanumber for catching the omission. [Daniel Lindsley]

- Removed erroneous old docs about Lucene support, which never landed.
  [Daniel Lindsley]

- Merge branch 'master' of github.com:toastdriven/django-haystack.
  [Daniel Lindsley]

- Fixed typo in the tutorial. Thanks fxdgear for pointing that out!
  [Daniel Lindsley]

- Fixed a bug related to Unicode data in conjunction with the ``dummy``
  backend. Thanks to kylemacfarlane for the report! [Daniel Lindsley]

- Added Forkinit to Who Uses. [Daniel Lindsley]

- Added Rampframe to Who Uses. [Daniel Lindsley]

- Added other apps documentation for Haystack-related apps. [Daniel
  Lindsley]

- Unified the way ``DEFAULT_OPERATOR`` is setup. [Daniel Lindsley]

- You can now override ``ITERATOR_LOAD_PER_QUERY`` with a setting if
  you're consuming big chunks of a ``SearchQuerySet``. Thanks to
  kylemacfarlane for the report. [Daniel Lindsley]

- Moved the preparation of faceting data to a
  ``SearchIndex.full_prepare()`` method for easier overriding. Thanks to
  xav for the suggestion! [Daniel Lindsley]

- The ``more_like_this`` tag now silently fails if things go south.
  Thanks to piquadrat for the patch! [Daniel Lindsley]

- Added a fleshed out ``simple_backend`` for basic usage + testing.
  [David Sauve]

- ``SearchView.build_form()`` now accepts a dict to pass along to the
  form. Thanks to traviscline for the patch! [Daniel Lindsley]

- Fixed the ``setup.py`` to include ``haystack.utils`` and added to the
  ``MANIFEST.in``. Thanks to jezdez for the patch! [Daniel Lindsley]

- Fixed date faceting in Solr. [Daniel Lindsley]

  No more OOMs and very fast over large data sets.

- Added the ``search_view_factory`` function for thread-safe use of
  ``SearchView``. [Daniel Lindsley]

- Added more to the docs about the ``SearchQuerySet.narrow()`` method to
  describe when/why to use it. [Daniel Lindsley]

- Fixed Whoosh tests. [Daniel Lindsley]

  Somewhere, a reference to the old index was hanging around causing incorrect failures.

- The Whoosh backed now uses the ``AsyncWriter``, which ought to provide
  better performance. Requires Whoosh 0.3.15 or greater. [Daniel
  Lindsley]

- Added a way to pull the correct fieldname, regardless if it's been
  overridden or not. [Daniel Lindsley]

- Added docs about adding new fields. [Daniel Lindsley]

- Removed a painful ``isinstance`` check which should make non-standard
  usages easier. [Daniel Lindsley]

- Updated docs regarding reserved field names in Haystack. [Daniel
  Lindsley]

- Pushed some of the new faceting bits down in the implementation.
  [Daniel Lindsley]

- Removed unnecessary fields from the Solr schema template. [Daniel
  Lindsley]

- Revamped how faceting is done within Haystack to make it easier to
  work with. [Daniel Lindsley]

- Add more sites to Who Uses. [Daniel Lindsley]

- Fixed a bug in ``ModelSearchIndex`` where the ``index_fieldname``
  would not get set. Also added a way to override it in a general
  fashion. Thanks to traviscline for the patch! [Daniel Lindsley]

- Backend API standardization. Thanks to batiste for the report! [Daniel
  Lindsley]

- Removed a method that was supposed to have been removed before 1.0.
  Oops. [Daniel Lindsley]

- Added the ability to override field names within the index. Thanks to
  traviscline for the suggestion and original patch! [Daniel Lindsley]

- Corrected the AUTHORS because slai actually provided the patch. Sorry
  about that. [Daniel Lindsley]

- Refined the internals of ``ModelSearchIndex`` to be a little more
  flexible. Thanks to traviscline for the patch! [Daniel Lindsley]

- The Whoosh backend now supports ``RamStorage`` for use with testing or
  other non-permanent indexes. [Daniel Lindsley]

- Fixed a bug in the ``Highlighter`` involving repetition and regular
  expressions. Thanks to alanzoppa for the original patch! [Daniel
  Lindsley]

- Fixed a bug in the Whoosh backend when a ``MultiValueField`` is empty.
  Thanks to alanwj for the original patch! [Daniel Lindsley]

- All dynamic imports now use ``importlib``. Thanks to bfirsh for the
  original patch mentioning this. [Daniel Lindsley]

  A backported version of ``importlib`` is included for compatibility with Django 1.0.

- Altered ``EmptySearchQuerySet`` so it's usable from templates. Thanks
  to bfirsh for the patch! [Daniel Lindsley]

- Added tests to ensure a Whoosh regression is no longer present.
  [Daniel Lindsley]

- Fixed a bug in Whoosh where using just ``.models()`` would create an
  invalid query. Thanks to ricobl for the original patch. [Daniel
  Lindsley]

- Forms with initial data now display it when used with SearchView.
  Thanks to osirius for the original patch. [Daniel Lindsley]

- App order is now consistent with INSTALLED_APPS when running
  ``update_index``. [Daniel Lindsley]

- Updated docs to reflect the recommended way to do imports in when
  defining ``SearchIndex`` classes. [Daniel Lindsley]

  This is not my preferred style but reduces the import errors some people experience.

- Fixed omission of Xapian in the settings docs. Thanks to flebel for
  pointing this out. [Daniel Lindsley]

- Little bits of cleanup related to testing. [Daniel Lindsley]

- Fixed an error in the docs related to pre-rendering data. [Daniel
  Lindsley]

- Added Pegasus News to Who Uses. [Daniel Lindsley]

- Corrected an import in forms for consistency. Thanks to bkonkle for
  pointing this out. [Daniel Lindsley]

- Fixed bug where passing a customized ``site`` would not make it down
  through the whole stack. Thanks to Peter Bengtsson for the report and
  original patch. [Daniel Lindsley]

- Bumped copyright years. [Daniel Lindsley]

- Changed Whoosh backend so most imports will raise the correct
  exception. Thanks to shabda for the suggestion. [Daniel Lindsley]

- Refactored Solr's tests to minimize reindexes. Runs ~50% faster.
  [Daniel Lindsley]

- Fixed a couple potential circular imports. [Daniel Lindsley]

- The same field can now have multiple query facets. Thanks to bfirsh
  for the original patch. [Daniel Lindsley]

- Added schema for testing Solr. [Daniel Lindsley]

- Fixed a string interpolation bug when adding an invalid data facet.
  Thanks to simonw for the original patch. [Daniel Lindsley]

- Fixed the default highlighter to give slightly better results,
  especially with short strings. Thanks to RobertGawron for the original
  patch. [Daniel Lindsley]

- Changed the ``rebuild_index`` command so it can take all options that
  can be passed to either ``clear_index`` or ``update_index``. Thanks to
  brosner for suggesting this. [Daniel Lindsley]

- Added ``--noinput`` flag to ``clear_index``. Thanks to aljosa for the
  suggestion. [Daniel Lindsley]

- Updated the example in the template to be a little more real-world and
  user friendly. Thanks to j0hnsmith for pointing this out. [Daniel
  Lindsley]

- Fixed a bug with the Whoosh backend where scores weren't getting
  populated correctly. Thanks to horribtastic for the report. [Daniel
  Lindsley]

- Changed ``EmptySearchQuerySet`` so it returns an empty list when
  slicing instead of mistakenly running queries. Thanks to askfor for
  reporting this bug. [Daniel Lindsley]

- Switched ``SearchView`` & ``FacetedSearchView`` to use
  ``EmptySearchQuerySet`` (instead of a regular list) when there are no
  results. Thanks to acdha for the original patch. [Daniel Lindsley]

- Added RedditGifts to "Who Uses". [Daniel Lindsley]

- Added Winding Road to "Who Uses". [Daniel Lindsley]

- Added ryszard's full name to AUTHORS. [Daniel Lindsley]

- Added initialization bits to part of the Solr test suite. Thanks to
  notanumber for pointing this out. [Daniel Lindsley]

- Started the 1.1-alpha work. Apologies for not doing this sooner.
  [Daniel Lindsley]

- Added an advanced setting for disabling Haystack's initialization in
  the event of a conflict with other apps. [Daniel Lindsley]

- Altered ``SearchForm`` to use ``.is_valid()`` instead of ``.clean()``,
  which is a more idiomatic/correct usage. Thanks to askfor for the
  suggestion. [Daniel Lindsley]

- Added MANIFEST to ignore list. [Daniel Lindsley]

- Fixed Django 1.0 compatibility when using the Solr backend. [Daniel
  Lindsley]

- Marked Haystack as 1.0 final. [Daniel Lindsley]

- Incorrect test result from changing the documented way the
  ``highlight`` template tag gets called. [Daniel Lindsley]

- Updated the example in faceting documentation to provide better
  results and explanation on the reasoning. [Daniel Lindsley]

- Added further documentation about
  ``SearchIndex``/``RealTimeSearchIndex``. [Daniel Lindsley]

- Added docs about `SearchQuerySet.highlight`. [toastdriven]

- Added further docs on `RealTimeSearchIndex`. [toastdriven]

- Added documentation on the ``RealTimeSearchIndex`` class.
  [toastdriven]

- Fixed the documentation for the arguments on the `highlight` tag.
  Thanks to lucalenardi for pointing this out. [Daniel Lindsley]

- Fixed tutorial to mention where the `NoteSearchIndex` should be
  placed. Thanks to bkeating for pointing this out. [Daniel Lindsley]

- Marked Haystack as 1.0.0 release candidate 1. [Daniel Lindsley]

- Haystack now requires Whoosh 0.3.5. [Daniel Lindsley]

- Last minute documentation cleanup. [Daniel Lindsley]

- Added documentation about the management commands that come with
  Haystack. [Daniel Lindsley]

- Added docs on the template tags included with Haystack. [Daniel
  Lindsley]

- Added docs on highlighting. [Daniel Lindsley]

- Removed some unneeded legacy code that was causing conflicts when
  Haystack was used with apps that load all models (such as `django-
  cms2`, `localemiddleware` or `django-transmeta`). [Daniel Lindsley]

- Removed old code from the `update_index` command. [Daniel Lindsley]

- Altered spelling suggestion test to something a little more
  consistent. [Daniel Lindsley]

- Added tests for slicing the end of a `RelatedSearchQuerySet`. [Daniel
  Lindsley]

- Fixed case where `SearchQuerySet.more_like_this` would fail when using
  deferred Models. Thanks to Alex Gaynor for the original patch. [Daniel
  Lindsley]

- Added default logging bits to prevent "No handlers found" message.
  [Daniel Lindsley]

- BACKWARD-INCOMPATIBLE: Renamed `reindex` management command to
  `update_index`, renamed `clear_search_index` management command to
  `clear_index` and added a `rebuild_index` command to both clear &
  reindex. [Daniel Lindsley]

- BACKWARD-INCOMPATIBLE: `SearchIndex` no longer hooks up
  `post_save/post_delete` signals for the model it's registered with.
  [Daniel Lindsley]

  If you use `SearchIndex`, you will have to manually cron up a `reindex` (soon to become `update_index`) management command to periodically refresh the data in your index.

  If you were relying on the old behavior, please use `RealTimeSearchIndex` instead, which does hook up those signals.

- Ensured that, if a `MultiValueField` is marked as `indexed=False` in
  Whoosh, it ought not to post-process the field. [Daniel Lindsley]

- Ensured data going into the indexes round-trips properly. Fixed
  `DateField`/`DateTimeField` handling for all backends and
  `MultiValueField` handling in Whoosh. [Daniel Lindsley]

- Added a customizable `highlight` template tag plus an underlying
  `Highlighter` implementation. [Daniel Lindsley]

- Added more documentation about using custom `SearchIndex.prepare_FOO`
  methods. [Daniel Lindsley]

- With Whoosh 0.3.5+, the number of open files is greatly reduced.
  [Daniel Lindsley]

- Corrected example in docs about `RelatedSearchQuerySet`. Thanks to
  askfor for pointing this out. [Daniel Lindsley]

- Altered `SearchResult` objects to fail gracefully when the
  model/object can't be found. Thanks to akrito for the report. [Daniel
  Lindsley]

- Fixed a bug where `auto_query` would fail to escape strings that
  pulled out for exact matching. Thanks to jefftriplett for the report.
  [Daniel Lindsley]

- Added Brick Design to Who Uses. [Daniel Lindsley]

- Updated backend support docs slightly. [Daniel Lindsley]

- Added the ability to combine `SearchQuerySet`s via `&` or `|`. Thanks
  to reesefrancis for the suggestion. [Daniel Lindsley]

- Revised the most of the tutorial. [Daniel Lindsley]

- Better documented how user-provided data should be sanitized. [Daniel
  Lindsley]

- Fleshed out the `SearchField` documentation. [Daniel Lindsley]

- Fixed formatting on ``SearchField`` documentation. [Daniel Lindsley]

- Added basic ``SearchField`` documentation. [Daniel Lindsley]

  More information about the kwargs and usage will be eventually needed.

- Bumped the `ulimit` so Whoosh tests pass consistently on Mac OS X.
  [Daniel Lindsley]

- Fixed the `default` kwarg in `SearchField` (and subclasses) to work
  properly from a user's perspective. [Daniel Lindsley]

- BACKWARD-INCOMPATIBLE: Fixed ``raw_search`` to cooperate when
  paginating/slicing as well as many other conditions. [Daniel Lindsley]

  This no longer immediately runs the query, nor pokes at any internals. It also now takes into account other details, such as sorting & faceting.

- Fixed a bug in the Whoosh backend where slicing before doing a hit
  count could cause strange results when paginating. Thanks to
  kylemacfarlane for the original patch. [Daniel Lindsley]

- The Whoosh tests now deal with the same data set as the Solr tests and
  cover various aspects better. [Daniel Lindsley]

- Started to pull out the real-time, signal-based updates out of the
  main `SearchIndex` class. Backward compatible for now. [Daniel
  Lindsley]

- Fixed docs to include `utils` documentation. [Daniel Lindsley]

- Updated instructions for installing `pysolr`. Thanks to sboisen for
  pointing this out. [Daniel Lindsley]

- Added acdha to AUTHORS for previous commit. [Daniel Lindsley]

- Added exception handling to the Solr Backend to silently fail/log when
  Solr is unavailable. Thanks to acdha for the original patch. [Daniel
  Lindsley]

- The `more_like_this` tag is now tested within the suite. Also has lots
  of cleanup for the other Solr tests. [Daniel Lindsley]

- On both the Solr & Whoosh backends, don't do an update if there's
  nothing being updated. [Daniel Lindsley]

- Moved Haystack's internal fields out of the backends and into
  `SearchIndex.prepare`. [Daniel Lindsley]

  This is both somewhat more DRY as well as a step toward Haystack being useful to non-Django projects.

- Fixed a bug in the `build_schema` where fields that aren't supposed to
  be indexed are still getting post-procesed by Solr. Thanks to Jonathan
  Slenders for the report. [Daniel Lindsley]

- Added HUGE to Who Uses. [Daniel Lindsley]

- Fixed bug in Whoosh where it would always generate spelling
  suggestions off the full query even when given a different query
  string to check against. [Daniel Lindsley]

- Simplified the SQ object and removed a limitation on kwargs/field
  names that could be passed in. Thanks to traviscline for the patch.
  [Daniel Lindsley]

- Documentation on `should_update` fixed to match the new signature.
  Thanks to kylemacfarlane for pointing this out. [Daniel Lindsley]

- Fixed missing words in Best Practices documentation. Thanks to
  frankwiles for the original patch. [Daniel Lindsley]

- The `update_object` method now passes along kwargs as needed to the
  `should_update` method. Thanks to askfor for the suggestion. [Daniel
  Lindsley]

- Updated docs about the removal of the Whoosh fork. [Daniel Lindsley]

- Removed extraneous `BadSearchIndex3` from test suite. Thanks
  notanumber! [Daniel Lindsley]

- We actually want `repr`, not `str`. [Daniel Lindsley]

- Pushed the `model_attr` check lower down into the `SearchField` and
  make it occur later, so that exceptions come at a point where Django
  can better deal with them. [Daniel Lindsley]

- Fixed attempting to access an invalid `model_attr`. Thanks to
  notanumber for the original patch. [Daniel Lindsley]

- Added SQ objects (replacing the QueryFilter object) as the means to
  generate queries/query fragments. Thanks to traviscline for all the
  hard work. [Daniel Lindsley]

  The SQ object is similar to Django's Q object and allows for arbitrarily complex queries. Only backward incompatible if you were relying on the SearchQuery/QueryFilter APIs.

- Reformatted debugging docs a bit. [Daniel Lindsley]

- Added debugging information about the Whoosh lock error. [Daniel
  Lindsley]

- Brought the TODO up to date. [Daniel Lindsley]

- Added a warning to the documentation about how `__startswith` may not
  always provide the expected results. Thanks to codysoyland for
  pointing this out. [Daniel Lindsley]

- Added debugging documentation, with more examples coming in the
  future. [Daniel Lindsley]

- Added a new `basic_search` view as a both a working example of how to
  write traditional views and as a thread-safe view, which the class-
  based ones may/may not be. [Daniel Lindsley]

- Fixed sample template in the documentation. Thanks to lemonad for
  pointing this out. [Daniel Lindsley]

- Updated documentation to include a couple more Sphinx directives.
  Index is now more useful. [Daniel Lindsley]

- Made links more obvious in documentation. [Daniel Lindsley]

- Added an `example_project` demonstrating how a sample project might be
  setup. [Daniel Lindsley]

- Fixed `load_backend` to use the argument passed instead of always the
  `settings.HAYSTACK_SEARCH_ENGINE`. Thanks to newgene for the report.
  [Daniel Lindsley]

- Regression where sometimes `narrow_queries` got juggled into a list
  when it should be a set everywhere. Thanks tcline & ericholscher for
  the report. [Daniel Lindsley]

- Updated the Whoosh backend's version requirement to reflect the fully
  working version of Whoosh. [Daniel Lindsley]

- With the latest SVN version of Whoosh (r344), `SearchQuerySet()` now
  works properly in Whoosh. [Daniel Lindsley]

- Added a `FacetedModelSearchForm`. Thanks to mcroydon for the original
  patch. [Daniel Lindsley]

- Added translation capabilities to the `SearchForm` variants. Thanks to
  hejsan for pointing this out. [Daniel Lindsley]

- Added AllForLocal to Who Uses. [Daniel Lindsley]

- The underlying caching has been fixed so it no longer has to fill the
  entire cache before it to ensure consistency. [Daniel Lindsley]

  This results in significantly faster slicing and reduced memory usage. The test suite is more complete and ensures this functionality better.

  This also removes `load_all_queryset` from the main `SearchQuerySet` implementation. If you were relying on this behavior, you should use `RelatedSearchQuerySet` instead.

- Log search queries with `DEBUG = True` for debugging purposes, similar
  to what Django does. [Daniel Lindsley]

- Updated LJ's Who Uses information. [Daniel Lindsley]

- Added Sunlight Labs & NASA to the Who Uses list. [Daniel Lindsley]

- Added Eldarion to the Who Uses list. [Daniel Lindsley]

- When more of the cache is populated, provide a more accurate `len()`
  of the `SearchQuerySet`. This ought to only affect advanced usages,
  like excluding previously-registered models or `load_all_queryset`.
  [Daniel Lindsley]

- Fixed a bug where `SearchQuerySet`s longer than `REPR_OUTPUT_SIZE`
  wouldn't include a note about truncation when `__repr__` is called.
  [Daniel Lindsley]

- Added the ability to choose which site is used when reindexing. Thanks
  to SmileyChris for pointing this out and the original patch. [Daniel
  Lindsley]

- Fixed the lack of a `__unicode__` method on `SearchResult` objects.
  Thanks to mint_xian for pointing this out. [Daniel Lindsley]

- Typo'd the setup.py changes. Thanks to jlilly for catching that.
  [Daniel Lindsley]

- Converted all query strings to Unicode for Whoosh. Thanks to simonw108
  for pointing this out. [Daniel Lindsley]

- Added template tags to `setup.py`. Thanks to Bogdan for pointing this
  out. [Daniel Lindsley]

- Added two more tests to the Whoosh backend, just to make sure. [Daniel
  Lindsley]

- Corrected the way Whoosh handles `order_by`. Thanks to Rowan for
  pointing this out. [Daniel Lindsley]

- For the Whoosh backend, ensure the directory is writable by the
  current user to try to prevent failed writes. [Daniel Lindsley]

- Added a better label to the main search form field. [Daniel Lindsley]

- Bringing the Whoosh backend up to version 0.3.0b14. This version of
  Whoosh has better query parsing, faster indexing and, combined with
  these changes, should cause fewer disruptions when used in a
  multiprocess/multithreaded environment. [Daniel Lindsley]

- Added optional argument to `spelling_suggestion` that lets you provide
  a different query than the one built by the SearchQuerySet. [Daniel
  Lindsley]

  Useful for passing along a raw user-provided query, especially when there is a lot of post-processing done.

- SearchResults now obey the type of data chosen in their corresponding
  field in the SearchIndex if present. Thanks to evgenius for the
  original report. [Daniel Lindsley]

- Fixed a bug in the Solr backend where submitting an empty string to
  search returned an ancient and incorrect datastructure. Thanks kapa77
  for the report. [Daniel Lindsley]

- Fixed a bug where the cache would never properly fill due to the
  number of results returned being lower than the hit count. This could
  happen when there were results excluded due to being in the index but
  the model NOT being registered in the `SearchSite`. Thanks akrito and
  tcline for the report. [Daniel Lindsley]

- Altered the docs to look more like the main site. [Daniel Lindsley]

- Added a (short) list of who uses Haystack. Would love to have more on
  this list. [Daniel Lindsley]

- Fixed docs on preparing data. Thanks fud. [Daniel Lindsley]

- Added the `ModelSearchIndex` class for easier `SearchIndex`
  generation. [Daniel Lindsley]

- Added a note about using possibly unsafe data with `filter/exclude`.
  Thanks to ryszard for pointing this out. [Daniel Lindsley]

- Standardized the API on `date_facet`. Thanks to notanumber for the
  original patch. [Daniel Lindsley]

- Moved constructing the schema down to the `SearchBackend` level. This
  allows more flexibility when creating a schema. [Daniel Lindsley]

- Fixed a bug where a hyphen provided to `auto_query` could break the
  query string. Thanks to ddanier for the report. [Daniel Lindsley]

- BACKWARD INCOMPATIBLE - For consistency, `get_query_set` has been
  renamed to `get_queryset` on `SearchIndex` classes. [Daniel Lindsley]

  A simple search & replace to remove the underscore should be all that is needed.

- Missed two bits while updating the documentation for the Xapian
  backend. [Daniel Lindsley]

- Updated documentation to add the Xapian backend information. A big
  thanks to notatnumber for all his hard work on the Xapian backend.
  [Daniel Lindsley]

- Added `EmptySearchQuerySet`. Thanks to askfor for the suggestion!
  [Daniel Lindsley]

- Added "Best Practices" documentation. [Daniel Lindsley]

- Added documentation about the `HAYSTACK_SITECONF` setting. [Daniel
  Lindsley]

- Fixed erroneous documentation on Xapian not supporting boost. Thanks
  notanumber! [Daniel Lindsley]

- BACKWARD INCOMPATIBLE - The `haystack.autodiscover()` and other site
  modifications now get their own configuration file and should no
  longer be placed in the `ROOT_URLCONF`. Thanks to SmileyChris for the
  original patch and patrys for further feedback. [Daniel Lindsley]

- Added `verbose_name_plural` to the `SearchResult` object. [Daniel
  Lindsley]

- Added a warning about ordering by integers with the Whoosh backend.
  [Daniel Lindsley]

- Added a note about ordering and accented characters. [Daniel Lindsley]

- Updated the `more_like_this` tag to allow for narrowing the models
  returned by the tag. [Daniel Lindsley]

- Fixed `null=True` for `IntegerField` and `FloatField`. Thanks to
  ryszard for the report and original patch. [Daniel Lindsley]

- Reverted aabdc9d4b98edc4735ed0c8b22aa09796c0a29ab as it would cause
  mod_wsgi environments to fail in conjunction with the admin on Django
  1.1. [Daniel Lindsley]

- Added the start of a glossary of terminology. [Daniel Lindsley]

- Various documentation fixes. Thanks to sk1p & notanumber. [Daniel
  Lindsley]

- The `haystack.autodiscover()` and other site modifications may now be
  placed in ANY URLconf, not just the `ROOT_URLCONF`. Thanks to
  SmileyChris for the original patch. [Daniel Lindsley]

- Fixed invalid/empty pages in the SearchView. Thanks to joep and
  SmileyChris for patches. [Daniel Lindsley]

- Added a note and an exception about consistent fieldnames for the
  document field across all `SearchIndex` classes. Thanks sk1p\_! [Daniel
  Lindsley]

- Possible thread-safety fix related to registration handling. [Daniel
  Lindsley]

- BACKWARD INCOMPATIBLE - The 'boost' method no longer takes kwargs.
  This makes boost a little more useful by allowing advanced terms.
  [Daniel Lindsley]

  To migrate code, convert multiple kwargs into separate 'boost' calls, quote what was the key and change the '=' to a ','.

- Updated documentation to match behavioral changes to MLT. [Daniel
  Lindsley]

- Fixed a serious bug in MLT on Solr. Internals changed a bit and now
  things work correctly. [Daniel Lindsley]

- Removed erroneous 'zip_safe' from setup.py. Thanks ephelon. [Daniel
  Lindsley]

- Added `null=True` to fields, allowing you to ignore/skip a field when
  indexing. Thanks to Kevin for the original patch. [Daniel Lindsley]

- Fixed a standing test failure. The dummy setup can't do `load_all` due
  to mocking. [Daniel Lindsley]

- Added initial `additional_query` to MLT to allow for narrowing
  results. [Daniel Lindsley]

- Fixed nasty bug where results would get duplicated due to cached
  results. [Daniel Lindsley]

- Altered `ITERATOR_LOAD_PER_QUERY` from 20 to 10. [Daniel Lindsley]

- Corrected tutorial when dealing with fields that have
  `use_template=True`. [Daniel Lindsley]

- Updated documentation to reflect basic Solr setup. [Daniel Lindsley]

- Fix documentation on grabbing Whoosh and on the 'load_all' parameter
  for SearchForms. [Daniel Lindsley]

- Fixed bug where the '__in' filter wouldn't work with phrases or data
  types other than one-word string/integer. [Daniel Lindsley]

- Fixed bug so that the 'load_all' option in 'SearchView' now actually
  does what it says it should. How embarrassing... [Daniel Lindsley]

- Added ability to specify custom QuerySets for loading records via
  'load_all'/'load_all_queryset'. [Daniel Lindsley]

- Fixed a bug where results from non-registered models could appear in
  the results. [Daniel Lindsley]

- BACKWARD INCOMPATIBLE - Changed 'module_name' to 'model_name'
  throughout Haystack related to SearchResult objects. Only incompatible
  if you were relying on this attribute. [Daniel Lindsley]

- Added the ability to fetch additional and stored fields from a
  SearchResult as well as documentation on the SearchResult itself.
  [Daniel Lindsley]

- Added the ability to look through relations in SearchIndexes via '__'.
  [Daniel Lindsley]

- Added note about the 'text' fieldname convention. [Daniel Lindsley]

- Added an 'update_object' and 'remove_object' to the SearchSite objects
  as a shortcut. [Daniel Lindsley]

- Recover gracefully from queries Whoosh judges to be invalid. [Daniel
  Lindsley]

- Missed test from previous commit. [Daniel Lindsley]

- Added stemming support to Whoosh. [Daniel Lindsley]

- Removed the commented version. [Daniel Lindsley]

- Django 1.0.X compatibility fix for the reindex command. [Daniel
  Lindsley]

- Reindexes should now consume a lot less RAM. [Daniel Lindsley]

  Evidently, when you run a ton of queries touching virtually everything in your DB, you need to clean out the "logged" queries from the connection. Sad but true.

- Altered `SearchBackend.remove` and `SearchBackend.get_identifier` to
  accept an object or a string identifier (in the event the object is no
  longer available). [Daniel Lindsley]

  This is useful in an environment where you no longer have the original object on hand and know what it is you wish to delete.

- Added a simple (read: ghetto) way to run the test suite without having
  to mess with settings. [Daniel Lindsley]

- Added a setting `HAYSTACK_BATCH_SIZE` to control how many objects are
  processed at once when running a reindex. [Daniel Lindsley]

- Fixed import that was issuing a warning. [Daniel Lindsley]

- Further tests to make sure `unregister` works appropriately as well,
  just to be paranoid. [Daniel Lindsley]

- Fixed a bizarre bug where backends may see a different site object
  than the rest of the application code. THIS REQUIRES SEARCH &
  REPLACING ALL INSTANCES OF `from haystack.sites import site` TO `from
  haystack import site`. [Daniel Lindsley]

  No changes needed if you've been using `haystack.autodiscover()`.

- Pushed save/delete signal registration down to the SearchIndex level.
  [Daniel Lindsley]

  This should make it easier to alter how individual indexes are setup, allowing you to queue updates, prevent deletions, etc. The internal API changed slightly.

- Created a default 'clean' implementation, as the first three (and soon
  fourth) backends all use identical code. [Daniel Lindsley]

- Updated tests to match new 'model_choices'. [Daniel Lindsley]

- Added timeout support to Solr. [Daniel Lindsley]

- Capitalize the Models in the model_choices. [Daniel Lindsley]

- Removed unnecessary import. [Daniel Lindsley]

- No longer need to watch for DEBUG in the 'haystack_info' command.
  [Daniel Lindsley]

- Fixed bug in Whoosh backend when spelling suggestions are disabled.
  [Daniel Lindsley]

- Added a "clear_search_index" management command. [Daniel Lindsley]

- Removed comments as pysolr now supports timeouts and the other comment
  no longer applies. [Daniel Lindsley]

- Removed Solr-flavored schema bits. [Daniel Lindsley]

  Still need to work out a better way to handle user created fields that don't fit neatly into subclassing one of the core Field types.

- Moved informational messages to a management command to behave better
  when using dumpdata or wsgi. [Daniel Lindsley]

- Changed some Solr-specific field names. Requires a reindex. [Daniel
  Lindsley]

- Typo'd docstring. [Daniel Lindsley]

- Removed empty test file from spelling testing. [Daniel Lindsley]

- Documentation for getting spelling support working on Solr. [Daniel
  Lindsley]

- Initial spelling support added. [Daniel Lindsley]

- Added a 'more_like_this' template tag. [Daniel Lindsley]

- Removed an unnecessary 'run'. This cause MLT (and potentially
  'raw_search') to fail by overwriting the results found. [Daniel
  Lindsley]

- Added Whoosh failure. Needs inspecting. [Daniel Lindsley]

- Finally added views/forms documentation. A touch rough still. [Daniel
  Lindsley]

- Fixed a bug in FacetedSearchView where a SearchQuerySet method could
  be called on an empty list instead. [Daniel Lindsley]

- More faceting documentation. [Daniel Lindsley]

- Started faceting documentation. [Daniel Lindsley]

- Updated docs to finally include details about faceting. [Daniel
  Lindsley]

- Empty or one character searches in Whoosh returned the wrong data
  structure. Thanks for catching this, silviogutierrez! [Daniel
  Lindsley]

- Added scoring to Whoosh now that 0.1.20+ support it. [Daniel Lindsley]

- Fixed a bug in the Solr tests due to recent changes in pysolr. [Daniel
  Lindsley]

- Added documentation on the 'narrow' method. [Daniel Lindsley]

- Added additional keyword arguments on raw_search. [Daniel Lindsley]

- Added 'narrow' support in Whoosh. [Daniel Lindsley]

- Fixed Whoosh backend's handling of pre-1900 dates. Thanks JoeGermuska!
  [Daniel Lindsley]

- Backed out the Whoosh quoted dates patch. [Daniel Lindsley]

  Something still seems amiss in the Whoosh query parser, as ranges and dates together don't seem to get parsed together properly.

- Added a small requirements section to the docs. [Daniel Lindsley]

- Added notes about enabling the MoreLikeThisHandler within Solr.
  [Daniel Lindsley]

- Revised how tests are done so each backend now gets its own test app.
  [Daniel Lindsley]

  All tests pass once again.

- Added 'startswith' filter. [Daniel Lindsley]

- Fixed the __repr__ method on QueryFilters. Thanks JoeGermuska for the
  original patch! [Daniel Lindsley]

- BACKWARDS INCOMPATIBLE - Both the Solr & Whoosh backends now provide
  native Python types back in SearchResults. [Daniel Lindsley]

  This also allows Whoosh to use native types better from the 'SearchQuerySet' API itself.

  This unfortunately will also require all Whoosh users to reindex, as the way some data (specifically datetimes/dates but applicable to others) is stored in the index.

- SearchIndexes now support inheritance. Thanks smulloni! [Daniel
  Lindsley]

- Added FacetedSearchForm to make handling facets easier. [Daniel
  Lindsley]

- Heavily refactored the SearchView to take advantage of being a class.
  [Daniel Lindsley]

  It should now be much easier to override bits without having to copy-paste the entire __call__ method, which was more than slightly embarrassing before.

- Fixed Solr backend so that it properly converts native Python types to
  something Solr can handle. Thanks smulloni for the original patch!
  [Daniel Lindsley]

- SearchResults now include a verbose name for display purposes. [Daniel
  Lindsley]

- Fixed reverse order_by's when using Whoosh. Thanks matt_c for the
  original patch. [Daniel Lindsley]

- Handle Whoosh stopwords behavior when provided a single character
  query string. [Daniel Lindsley]

- Lightly refactored tests to only run engines with their own settings.
  [Daniel Lindsley]

- Typo'd the tutorial when setting up your own SearchSite. Thanks
  mcroydon! [Daniel Lindsley]

- Altered loading statements to only display when DEBUG is True. [Daniel
  Lindsley]

- Write to STDERR where appropriate. Thanks zerok for suggesting this
  change. [Daniel Lindsley]

- BACKWARD INCOMPATIBLE - Altered the search query param to 'q' instead
  of 'query'. Thanks simonw for prompting this change. [Daniel Lindsley]

- Removed the Whoosh patch in favor of better options. Please see the
  documentation. [Daniel Lindsley]

- Added Whoosh patch for 0.1.15 to temporarily fix reindexes. [Daniel
  Lindsley]

- Altered the reindex command to handle inherited models. Thanks
  smulloni! [Daniel Lindsley]

- Removed the no longer needed Whoosh patch. [Daniel Lindsley]

  Whoosh users should upgrade to the latest Whoosh (0.1.15) as it fixes the issues that the patch covers as well as others.

- Documented the 'content' shortcut. [Daniel Lindsley]

- Fixed an incorrect bit of documentation on the default operator
  setting. Thanks benspaulding! [Daniel Lindsley]

- Added documentation about Haystack's various settings. [Daniel
  Lindsley]

- Corrected an issue with the Whoosh backend that can occur when no
  indexes are registered. Now provides a better exception. [Daniel
  Lindsley]

- Documentation fixes. Thanks benspaulding! [Daniel Lindsley]

- Fixed Whoosh patch, which should help with the "KeyError" exceptions
  when searching with models. Thanks Matias Costa! [Daniel Lindsley]

- Improvements to the setup.py. Thanks jezdez & ask! [Daniel Lindsley]

- Fixed the .gitignore. Thanks ask! [Daniel Lindsley]

- FacetedSearchView now inherits from SearchView. Thanks cyberdelia!
  [Daniel Lindsley]

  This will matter much more soon, as SearchView is going to be refactored to be more useful and extensible.

- Documentation fixes. [Daniel Lindsley]

- Altered the whoosh patch. Should apply cleanly now. [Daniel Lindsley]

- Better linking to the search engine installation notes. [Daniel
  Lindsley]

- Added documentation on setting up the search engines. [Daniel
  Lindsley]

- Provide an exception when importing a backend dependency fails. Thanks
  brosner for the initial patch. [Daniel Lindsley]

- Yay stupid typos! [Daniel Lindsley]

- Relicensing under BSD. Thanks matt_c for threatening to use my name in
  an endorsement of a derived product! [Daniel Lindsley]

- Fixed a bug in ModelSearchForm. Closes #1. Thanks dotsphinx! [Daniel
  Lindsley]

- Added link to pysolr binding. [Daniel Lindsley]

- Refined documentation on preparing SearchIndex data. [Daniel Lindsley]

- Changed existing references from 'model_name' to 'module_name'.
  [Daniel Lindsley]

  This was done to be consistent both internally and with Django. Thanks brosner!

- Documentation improvements. Restyled and friendlier intro page.
  [Daniel Lindsley]

- Added documentation on preparing data. [Daniel Lindsley]

- Additions and re-prioritizing the TODO list. [Daniel Lindsley]

- Added warnings to Whoosh backend in place of silently ignoring
  unsupported features. [Daniel Lindsley]

- Corrected Xapian's capabilities. Thanks richardb! [Daniel Lindsley]

- BACKWARD INCOMPATIBLE - Altered all settings to be prefixed with
  HAYSTACK\_. Thanks Collin! [Daniel Lindsley]

- Test cleanup from previous commits. [Daniel Lindsley]

- Changed the DEFAULT_OPERATOR back to 'AND'. Thanks richardb! [Daniel
  Lindsley]

- Altered the way registrations get handled. [Daniel Lindsley]

- Various fixes. Thanks brosner! [Daniel Lindsley]

- Added new 'should_update' method to documentation. [Daniel Lindsley]

- Added 'should_update' method to SearchIndexes. [Daniel Lindsley]

  This allows you to control, on a per-index basis, what conditions will cause an individual object to reindex. Useful for models that update frequently with changes that don't require indexing.

- Added FAQ docs. [Daniel Lindsley]

- Alter Whoosh backend to commit regardless. This avoids locking issues
  that can occur on higher volume sites. [Daniel Lindsley]

- A more efficient implementation of index clearing in Whoosh. [Daniel
  Lindsley]

- Added details about settings needed in settings.py. [Daniel Lindsley]

- Added setup.py. Thanks cyberdelia for prompting it. [Daniel Lindsley]

- Reindex management command now can reindex a limited range (like last
  24 hours). Thanks traviscline. [Daniel Lindsley]

- More things to do. [Daniel Lindsley]

- Documentation formatting fixes. [Daniel Lindsley]

- Added SearchBackend docs. [Daniel Lindsley]

- Corrected reST formatting. [Daniel Lindsley]

- Additional TODO's. [Daniel Lindsley]

- Initial SearchIndex documentation. [Daniel Lindsley]

- Formally introduced the TODO. [Daniel Lindsley]

- Updated backend support list. [Daniel Lindsley]

- Added initial documentation for SearchSites. [Daniel Lindsley]

- Changed whoosh backend to fix limiting sets. Need to revisit someday.
  [Daniel Lindsley]

- Added patch for Whoosh backend and version notes in documentation.
  [Daniel Lindsley]

- Initial Whoosh backend complete. [Daniel Lindsley]

  Does not yet support highlighting or scoring.

- Removed some unnecessary dummy code. [Daniel Lindsley]

- Work on trying to get the default site to load reliably in all cases.
  [Daniel Lindsley]

- Trimmed down the urls for tests now that the dummy backend works
  correctly. [Daniel Lindsley]

- Dummy now correctly loads the right SearchBackend. [Daniel Lindsley]

- Removed faceting from the default SearchView. [Daniel Lindsley]

- Refactored tests so they are no longer within the haystack app.
  [Daniel Lindsley]

  Further benefits include less mocking and haystack's tests no longer contributing overall testing of end-user apps. Documentation included.

- Removed old comment. [Daniel Lindsley]

- Fixed a potential race condition. Also, since there's no way to tell
  when everything is ready to go in Django, adding an explicit call to
  SearchQuerySet's __init__ to force the site to load if it hasn't
  already. [Daniel Lindsley]

- More tests on models() support. [Daniel Lindsley]

- Pulled schema building out into the site to leverage across backends.
  [Daniel Lindsley]

- Altered backend loading for consistency with Django and fixed the
  long-incorrect-for-non-obvious-and-tedious-reasons version number.
  Still beta but hopefully that changes soon. [Daniel Lindsley]

- Missed a spot when fixing SearchSites. [Daniel Lindsley]

- BACKWARD INCOMPATIBLE - Created a class name conflict during the last
  change (double use of ``SearchIndex``). Renamed original
  ``SearchIndex`` to ``SearchSite``, which is slightly more correct
  anyhow. [Daniel Lindsley]

  This will only affect you if you've custom built sites (i.e. not used ``autodiscover()``.

- More documentation. Started docs on SearchQuery. [Daniel Lindsley]

- Further fleshed out SearchQuerySet documentation. [Daniel Lindsley]

- BACKWARD INCOMPATIBLE (2 of 2) - Altered autodiscover to search for
  'search_indexes.py' instead of 'indexes.py' to prevent collisions and
  be more descriptive. [Daniel Lindsley]

- BACKWARD INCOMPATIBLE (1 of 2) - The ModelIndex class has been renamed
  to be SearchIndex to make room for future improvements. [Daniel
  Lindsley]

- Fleshed out a portion of the SearchQuerySet documentation. [Daniel
  Lindsley]

- SearchQuerySet.auto_query now supports internal quoting for exact
  matches. [Daniel Lindsley]

- Fixed semi-serious issue with SearchQuery objects, causing bits to
  leak from one query to the next when cloning. [Daniel Lindsley]

- Altered Solr port for testing purposes. [Daniel Lindsley]

- Now that Solr and core feature set are solid, moved haystack into beta
  status. [Daniel Lindsley]

- Added simple capabilities for retrieving facets back. [Daniel
  Lindsley]

- Bugfix to make sure model choices don't get loaded until after the
  IndexSite is populated. [Daniel Lindsley]

- Initial faceting support complete. [Daniel Lindsley]

- Query facets tested. [Daniel Lindsley]

- Bugfix to (field) facets. [Daniel Lindsley]

  Using a dict is inappropriate, as the output from Solr
  is sorted by count. Now using a two-tuple.

- Backward-incompatible changes to faceting. Date-based faceting is now
  present. [Daniel Lindsley]

- Solr implementation of faceting started. Needs more tests. [Daniel
  Lindsley]

- Initial faceting support in place. Needs more thought and a Solr
  implementation. [Daniel Lindsley]

- Unbreak iterables in queries. [Daniel Lindsley]

- Bugfixes for Unicode handling and loading deleted models. [Daniel
  Lindsley]

- Fixed bug in Solr's run method. [Daniel Lindsley]

- Various bug fixes. [Daniel Lindsley]

- Backward-Incompatible: Refactored ModelIndexes to allow greater
  customization before indexing. See "prepare()" methods. [Daniel
  Lindsley]

- Updated "build_solr_schema" command for revised fields. [Daniel
  Lindsley]

- Refactored SearchFields. Lightly backwards-incompatible. [Daniel
  Lindsley]

- No more duplicates from the "build_solr_schema" management command.
  [Daniel Lindsley]

- Removed the kwargs. Explicit is better than implicit. [Daniel
  Lindsley]

- Tests for highlighting. [Daniel Lindsley]

- Added initial highlighting support. Needs tests and perhaps a better
  implementation. [Daniel Lindsley]

- Started "build_solr_schema" command. Needs testing with more than one
  index. [Daniel Lindsley]

- Argh. ".select_related()" is killing reindexes. Again. [Daniel
  Lindsley]

- Stored fields now come back as part of the search result. [Daniel
  Lindsley]

- Fixed Solr's SearchQuery.clean to handle reserved words more
  appropriately. [Daniel Lindsley]

- Filter types seem solid and have tests. [Daniel Lindsley]

- App renamed (for namespace/sanity/because it's really different
  reasons). [Daniel Lindsley]

- Started trying to support the various filter types. Needs testing and
  verification. [Daniel Lindsley]

- Fixed tests in light of the change to "OR". [Daniel Lindsley]

- Readded "select_related" to reindex command. [Daniel Lindsley]

- I am a moron. [Daniel Lindsley]

- "OR" is now the default operator. Also, "auto_query" now handles
  not'ed keywords. [Daniel Lindsley]

- "More Like This" now implemented and functioning with Solr backend.
  [Daniel Lindsley]

- Removed broken references to __name__. [Daniel Lindsley]

- Internal documentation fix. [Daniel Lindsley]

- Solr backend can now clear on a per-model basis. [Daniel Lindsley]

- Solr backend tests fleshed out. Initial stability of Solr. [Daniel
  Lindsley]

  This needs more work (as does everything) but it seems to be working reliably from my testing (both unit and "real-world"). Onward and upward.

- Massive renaming/refactoring spree. Tests 100% passing again. [Daniel
  Lindsley]

- Renamed BaseSearchQuerySet to SearchQuerySet. Now requires
  instantiation. [Daniel Lindsley]

- Standardizing syntax. [Daniel Lindsley]

- Backend support update. [Daniel Lindsley]

- An attempt to make sure the main IndexSite is always setup, even
  outside web requests. Also needs improvement. [Daniel Lindsley]

- Reindexes now work. [Daniel Lindsley]

- Some painful bits to make things work for now. Needs improvement.
  [Daniel Lindsley]

- Support kwargs on the search. [Daniel Lindsley]

- Move solr backend tests in prep for fully testing the backend. [Daniel
  Lindsley]

- Some ContentField/StoredField improvements. [Daniel Lindsley]

  StoredFields now have a unique template per field (as they should have from the start) and there's a touch more checking. You can also now override the template name for either type of field.

- Fixed backend loading upon unpickling SearchBackend. [Daniel Lindsley]

- Tweak internal doc. [Daniel Lindsley]

- MOAR DOCS. [Daniel Lindsley]

- Internal documentation and cleanup. Also alters the behavior of
  SearchQuerySet's "order_by" method slightly, bringing it more in-line
  with QuerySet's behavior. [Daniel Lindsley]

- Documentation/license updates. [Daniel Lindsley]

- Fixed ModelIndexes and created tests for them. 100% tests passing
  again. [Daniel Lindsley]

- Started refactoring ModelIndexes. Needs tests (and possibly a little
  love). [Daniel Lindsley]

- Implemented Solr's boost, clean, multiple order-by. Fixed Solr's score
  retrieval (depends on custom pysolr) and exact match syntax. [Daniel
  Lindsley]

- Minor changes/cleanup. [Daniel Lindsley]

- Updated docs and a FIXME. [Daniel Lindsley]

- SearchView/SearchForm tests passing. [Daniel Lindsley]

- Changed BaseSearchQuery to accept a SearchBackend instance instead of
  the class. [Daniel Lindsley]

- Better dummy implementation, a bugfix to raw_search and
  SearchView/SearchForm tests. [Daniel Lindsley]

- Temporarily changed the Solr backend to ignore fields. Pysolr will
  need a patch and then reenable this. [Daniel Lindsley]

- Merge branch 'master' of
  ssh://daniel@mckenzie/home/daniel/djangosearch_refactor into HEAD.
  [Daniel Lindsley]

- Started SearchView tests and added URLconf. [Daniel Lindsley]

- Started SearchView tests and added URLconf. [Daniel Lindsley]

- Added note about basic use. Needs refactoring. [Matt Croydon]

- Merged index.rst. [Matt Croydon]

- Fixed result lookups when constructing a SearchResult. [Daniel
  Lindsley]

- Added more docs. [Daniel Lindsley]

- Added FIXME for exploration on Solr backend. [Daniel Lindsley]

- Solr's SearchQuery now handles phrases (exact match). [Daniel
  Lindsley]

- More work on the Solr backend. [Daniel Lindsley]

- Added more imports for future test coverage. [Daniel Lindsley]

- Added stubs for backend tests. [Daniel Lindsley]

- Documentation updates. [Daniel Lindsley]

- Refactored forms/views. Needs tests. [Daniel Lindsley]

- Removed old entries in .gitignore. [Daniel Lindsley]

- Implemented load_all. [Daniel Lindsley]

- Fixed query result retrieval. [Daniel Lindsley]

- Updated documentation index and tweaked overview formatting. [Matt
  Croydon]

- Slight docs improvements. [Daniel Lindsley]

- Started work on Solr backend. [Daniel Lindsley]

- Ignore _build. [Matt Croydon]

- Refactored documentation to format better in Sphinx. [Matt Croydon]

- Added _build to .gitignore. [Matt Croydon]

- Added sphinx config for documentation. [Matt Croydon]

- Verified _fill_cache behavior. 100% test pass. [Daniel Lindsley]

- Added a couple new desirable bits of functionality. Mostly stubbed.
  [Daniel Lindsley]

- Removed fixme and updated docs. [Daniel Lindsley]

- Removed an old reference to SearchPaginator. [Daniel Lindsley]

- Updated import paths to new backend Base* location. [Daniel Lindsley]

- Relocated base backend classes to __init__.py for consistency with
  Django. [Daniel Lindsley]

- BaseSearchQuerySet initial API complete and all but working. One
  failing test related to caching results. [Daniel Lindsley]

- Added new (improved?) template path for index templates. [Daniel
  Lindsley]

- Removed SearchPaginator, as it no longer provides anything over the
  standard Django Paginator. [Daniel Lindsley]

- Added len/iter support to BaseSearchQuerySet. Need to finish getitem
  support and test. [Daniel Lindsley]

- Started to update ModelIndex. [Daniel Lindsley]

- Started to alter dummy to match new class names/API. [Daniel Lindsley]

- Little bits of cleanup. [Daniel Lindsley]

- Added overview of where functionality belongs in djangosearch. This
  should likely make it's way into other docs and go away eventually.
  [Daniel Lindsley]

- BaseSearchQuery now tracks filters via QueryFilter objects. Tests
  complete for QueryFilter and nearly complete for BaseSearchQuery.
  [Daniel Lindsley]

- Started docs on creating new backends. [Daniel Lindsley]

- Started tests for BaseSearchQuery and BaseSearchQuerySet. [Daniel
  Lindsley]

- Fixed site loading. [Daniel Lindsley]

- More work on the Base* classes. [Daniel Lindsley]

- Started docs on creating new backends. [Daniel Lindsley]

- Yet more work on BaseSearchQuerySet. Now with fewer FIXMEs. [Daniel
  Lindsley]

- More work on BaseSearchQuerySet and added initial BaseSearchQuery
  object. [Daniel Lindsley]

- Removed another chunk of SearchPaginator as SearchQuerySet becomes
  more capable. Hopefully, SearchPaginator will simply go away soon.
  [Daniel Lindsley]

- Fixed ModelSearchForm to check the site's registered models. [Daniel
  Lindsley]

- Reenabled how other backends might load. [Daniel Lindsley]

- Added ignores. [Daniel Lindsley]

- Started documenting what backends are supported and what they can do.
  [Daniel Lindsley]

- More work on SearchQuerySet. [Daniel Lindsley]

- More renovation and IndexSite's tests pass 100%. [Daniel Lindsley]

- Fleshed out sites tests. Need to setup environment in order to run
  them. [Daniel Lindsley]

- Started adding tests. [Daniel Lindsley]

- First blush at SearchQuerySet. Non-functional, trying to lay out API
  and basic funationality. [Daniel Lindsley]

- Removed old results.py in favor of the coming SearchQuerySet. [Daniel
  Lindsley]

- Noted future improvements on SearchPaginator. [Daniel Lindsley]

- Removed old reference to autodiscover and added default site a la NFA.
  [Daniel Lindsley]

- Commented another use of RELEVANCE. [Daniel Lindsley]

- Little backend tweaks. [Daniel Lindsley]

- Added autodiscover support. [Daniel Lindsley]

- Readded management command. [Daniel Lindsley]

- Added SearchView and ModelSearchForm back in. Needs a little work.
  [Daniel Lindsley]

- Readded results. Need to look at SoC for ideas. [Daniel Lindsley]

- Readded paginator. Needs docs/tests. [Daniel Lindsley]

- Readded core backends + solr. Will add others as they reach 100%
  functionality. [Daniel Lindsley]

- Added ModelIndex back in. Customized to match new setup. [Daniel
  Lindsley]

- Added signal registration as well as some introspection capabilities.
  [Daniel Lindsley]

- Initial commit. Basic IndexSite implementation complete. Needs tests.
  [Daniel Lindsley]


