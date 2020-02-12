# encoding: utf-8
import os
from tempfile import mkdtemp

SECRET_KEY = "Please do not spew DeprecationWarnings"

# Haystack settings for running tests.
DATABASES = {
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": "haystack_tests.db"}
}

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "haystack",
    "test_haystack.discovery",
    "test_haystack.core",
    "test_haystack.spatial",
    "test_haystack.multipleindex",
    # This app exists to confirm that nothing breaks when INSTALLED_APPS has an app without models.py
    # which is common in some cases for things like admin extensions, reporting, etc.
    "test_haystack.test_app_without_models",
    # Confirm that everything works with app labels which have more than one level of hierarchy
    # as reported in https://github.com/django-haystack/django-haystack/issues/1152
    "test_haystack.test_app_with_hierarchy.contrib.django.hierarchal_app_django",
    "test_haystack.test_app_using_appconfig.apps.SimpleTestAppConfig",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "test_haystack.core.urls"

HAYSTACK_ROUTERS = [
    "haystack.routers.DefaultRouter",
    "test_haystack.multipleindex.routers.MultipleIndexRouter",
]

HAYSTACK_CONNECTIONS = {
    "default": {"ENGINE": "test_haystack.mocks.MockEngine"},
    "whoosh": {
        "ENGINE": "haystack.backends.whoosh_backend.WhooshEngine",
        "PATH": mkdtemp(prefix="test_whoosh_query"),
        "INCLUDE_SPELLING": True,
    },
    "filtered_whoosh": {
        "ENGINE": "haystack.backends.whoosh_backend.WhooshEngine",
        "PATH": mkdtemp(prefix="haystack-multipleindex-filtered-whoosh-tests-"),
        "EXCLUDED_INDEXES": ["test_haystack.multipleindex.search_indexes.BarIndex"],
    },
    "elasticsearch": {
        "ENGINE": "haystack.backends.elasticsearch_backend.ElasticsearchSearchEngine",
        "URL": os.environ.get("TEST_ELASTICSEARCH_1_URL", "http://localhost:9200/"),
        "INDEX_NAME": "test_default",
        "INCLUDE_SPELLING": True,
    },
    "simple": {"ENGINE": "haystack.backends.simple_backend.SimpleEngine"},
    "solr": {
        "ENGINE": "haystack.backends.solr_backend.SolrEngine",
        "URL": os.environ.get(
            "TEST_SOLR_URL", "http://localhost:9001/solr/collection1"
        ),
        "ADMIN_URL": os.environ.get(
            "TEST_SOLR_ADMIN_URL", "http://localhost:9001/solr/admin/cores"
        ),
        "INCLUDE_SPELLING": True,
    },
}

if "elasticsearch" in HAYSTACK_CONNECTIONS:
    try:
        import elasticsearch

        if (2,) <= elasticsearch.__version__ <= (3,):
            HAYSTACK_CONNECTIONS["elasticsearch"].update(
                {
                    "ENGINE": "haystack.backends.elasticsearch2_backend.Elasticsearch2SearchEngine"
                }
            )
        elif (5,) <= elasticsearch.__version__ <= (6,):
            HAYSTACK_CONNECTIONS["elasticsearch"].update(
                {
                    "ENGINE": "haystack.backends.elasticsearch5_backend.Elasticsearch5SearchEngine"
                }
            )
    except ImportError:
        del HAYSTACK_CONNECTIONS["elasticsearch"]
