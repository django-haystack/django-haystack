from django.core.management import call_command
from django.core.management.base import BaseCommand

from .update_index import DEFAULT_MAX_RETRIES


class Command(BaseCommand):
    help = "Completely rebuilds the search index by removing the old data and then updating."  # noqa A003

    def add_arguments(self, parser):
        parser.add_argument(
            "--noinput",
            action="store_false",
            dest="interactive",
            default=True,
            help="If provided, no prompts will be issued to the user and the data will be wiped out.",
        )
        parser.add_argument(
            "-u",
            "--using",
            action="append",
            default=[],
            help="Update only the named backend (can be used multiple times). "
            "By default all backends will be updated.",
        )
        parser.add_argument(
            "-k",
            "--workers",
            default=0,
            type=int,
            help="Allows for the use multiple workers to parallelize indexing. Requires multiprocessing.",
        )
        parser.add_argument(
            "--nocommit",
            action="store_false",
            dest="commit",
            default=True,
            help="Will pass commit=False to the backend.",
        )
        parser.add_argument(
            "-b",
            "--batch-size",
            dest="batchsize",
            type=int,
            help="Number of items to index at once.",
        )
        parser.add_argument(
            "-t",
            "--max-retries",
            action="store",
            dest="max_retries",
            type=int,
            default=DEFAULT_MAX_RETRIES,
            help="Maximum number of attempts to write to the backend when an error occurs.",
        )

    def handle(self, **options):
        clear_options = options.copy()
        update_options = options.copy()
        for key in ("batchsize", "workers", "max_retries"):
            del clear_options[key]
        for key in ("interactive",):
            del update_options[key]
        try:
            call_command("clear_index", **clear_options)
        except TypeError:
            """
            TypeError: clear_index: {'verbosity': 1, 'settings': None, 'pythonpath': None, 'traceback': False, 'no_color': False, 'force_color': False,
                'skip_checks': True, 'interactive': False, 'using': [], 'commit': False}
            Valid options are: commit, force_color, help, interactive, no_color, nocommit, noinput, pythonpath, settings, skip_checks, stderr, stdout, traceback,
                using, verbosity, version.
            Missing options are: help, nocommit, noinput, stderr, stdout, version.
            """
            from pathlib import Path

            here = Path(__file__).parent
            with (here / "stderr.txt").open("w") as stderr, (here / "stdout.txt").open(
                "w"
            ) as stdout:
                clear_options["stderr"] = stderr
                clear_options["stdout"] = stdout
                try:
                    call_command("clear_index", **clear_options)
                except TypeError:
                    raise TypeError(f"clear_index: {clear_options}")
        try:
            call_command("update_index", **update_options)
        except TypeError:
            raise TypeError(f"update_index: {update_options}")
