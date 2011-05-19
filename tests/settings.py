# Haystack settings for running tests.
DATABASES = {
    'default': {
        'ENGINE': 'sqlite3',
        'NAME': 'haystack_tests.db',
    }
}

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'haystack',
    'core',
]

ROOT_URLCONF = 'core.urls'

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'core.tests.mocks.MockEngine',
    },
}
