from unittest.mock import call, patch

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase

__all__ = ["CoreManagementCommandsTestCase"]


class CoreManagementCommandsTestCase(TestCase):
    @patch("haystack.management.commands.update_index.Command.update_backend")
    def test_update_index_default_using(self, m):
        """update_index uses default index when --using is not present"""
        call_command("update_index")
        for k in settings.HAYSTACK_CONNECTIONS:
            self.assertTrue(call("core", k) in m.call_args_list)

    @patch("haystack.management.commands.update_index.Command.update_backend")
    def test_update_index_using(self, m):
        """update_index only applies to indexes specified with --using"""
        call_command("update_index", verbosity=0, using=["eng", "fra"])
        m.assert_any_call("core", "eng")
        m.assert_any_call("core", "fra")
        self.assertTrue(
            call("core", "default") not in m.call_args_list,
            "update_index should have been restricted to the index specified with --using",
        )

    @patch("haystack.loading.ConnectionHandler.__getitem__")
    def test_clear_index_default_using(self, m):
        """clear_index uses all keys when --using is not present"""
        call_command("clear_index", verbosity=0, interactive=False)
        self.assertEqual(len(settings.HAYSTACK_CONNECTIONS), m.call_count)
        for k in settings.HAYSTACK_CONNECTIONS:
            self.assertTrue(call(k) in m.call_args_list)

    @patch("haystack.loading.ConnectionHandler.__getitem__")
    def test_clear_index_using(self, m):
        """clear_index only applies to indexes specified with --using"""

        call_command("clear_index", verbosity=0, interactive=False, using=["eng"])
        m.assert_called_with("eng")
        self.assertTrue(
            m.return_value.get_backend.called, "backend.clear() should be called"
        )
        self.assertTrue(
            call("default") not in m.call_args_list,
            "clear_index should have been restricted to the index specified with --using",
        )

    @patch("haystack.loading.ConnectionHandler.__getitem__")
    @patch("haystack.management.commands.update_index.Command.update_backend")
    def test_rebuild_index_default_using(self, m1, m2):
        """rebuild_index uses default index when --using is not present"""

        call_command("rebuild_index", verbosity=0, interactive=False)
        self.assertEqual(len(settings.HAYSTACK_CONNECTIONS), m2.call_count)
        for k in settings.HAYSTACK_CONNECTIONS:
            self.assertTrue(call(k) in m2.call_args_list)
        m1.assert_any_call("core", "default")
        m1.assert_any_call("core", "whoosh")

    @patch("haystack.loading.ConnectionHandler.__getitem__")
    @patch("haystack.management.commands.update_index.Command.update_backend")
    def test_rebuild_index_using(self, m1, m2):
        """rebuild_index passes --using to clear_index and update_index"""

        call_command("rebuild_index", verbosity=0, interactive=False, using=["eng"])
        m2.assert_called_with("eng")
        m1.assert_any_call("core", "eng")

    @patch("haystack.management.commands.update_index.Command.handle", return_value="")
    @patch("haystack.management.commands.clear_index.Command.handle", return_value="")
    def test_rebuild_index(self, mock_handle_clear, mock_handle_update):
        call_command("rebuild_index", interactive=False)

        self.assertTrue(mock_handle_clear.called)
        self.assertTrue(mock_handle_update.called)

    @patch("haystack.management.commands.update_index.Command.handle")
    @patch("haystack.management.commands.clear_index.Command.handle")
    def test_rebuild_index_nocommit(self, *mocks):
        call_command("rebuild_index", interactive=False, commit=False)

        for m in mocks:
            self.assertEqual(m.call_count, 1)

            args, kwargs = m.call_args

            self.assertIn("commit", kwargs)
            self.assertEqual(False, kwargs["commit"])

    @patch("haystack.management.commands.clear_index.Command.handle", return_value="")
    @patch("haystack.management.commands.update_index.Command.handle", return_value="")
    def test_rebuild_index_nocommit(self, update_mock, clear_mock):
        """
        Confirm that command-line option parsing produces the same results as using call_command() directly,
        mostly as a sanity check for the logic in rebuild_index which combines the option_lists for its
        component commands.
        """
        from haystack.management.commands.rebuild_index import Command

        Command().run_from_argv(
            ["django-admin.py", "rebuild_index", "--noinput", "--nocommit"]
        )

        for m in (clear_mock, update_mock):
            self.assertEqual(m.call_count, 1)

            args, kwargs = m.call_args

            self.assertIn("commit", kwargs)
            self.assertEqual(False, kwargs["commit"])

        args, kwargs = clear_mock.call_args

        self.assertIn("interactive", kwargs)
        self.assertIs(kwargs["interactive"], False)
