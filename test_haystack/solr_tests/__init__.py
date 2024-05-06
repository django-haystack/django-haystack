import os

from ..utils import check_solr


def load_tests(loader, standard_tests, pattern):
    check_solr()
    package_tests = loader.discover(
        start_dir=os.path.dirname(__file__), pattern=pattern
    )
    standard_tests.addTests(package_tests)
    return standard_tests
