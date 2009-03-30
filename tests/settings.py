# Haystack settings for running tests.
DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = 'haystack_tests.db'

INSTALLED_APPS = [
    'haystack',
    'core',
]

ROOT_URLCONF = 'core.urls'

SEARCH_ENGINE = 'dummy'
