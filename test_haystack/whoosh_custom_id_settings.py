"""Settings for the HAYSTACK_ID_FIELD regression test.

Loaded only by that test process, before Haystack imports ``constants.ID``.
"""

SECRET_KEY = "custom-id-field-test"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "haystack",
    "test_haystack.core",
]

HAYSTACK_ID_FIELD = "haystack_id"

HAYSTACK_CONNECTIONS = {
    "default": {
        "ENGINE": "haystack.backends.whoosh_backend.WhooshEngine",
        "STORAGE": "ram",
    }
}
