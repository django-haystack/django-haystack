from django.test import TestCase
from haystack.signals import BaseSignalProcessor, RealtimeSignalProcessor


class BaseSignalProcessorTestCase(TestCase):
    def test_init(self):
        pass

    def test_setup(self):
        pass

    def test_teardown(self):
        pass

    def test_handle_save(self):
        pass

    def test_handle_delete(self):
        pass


class RealtimeSignalProcessorTestCase(TestCase):
    def test_setup(self):
        pass

    def test_teardown(self):
        pass
