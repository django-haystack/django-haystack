# encoding: utf-8
from mock import call, patch

import django
from django.template import Template, Context
from django.test import TestCase
from django.utils import unittest

from ..core.models import MockModel


@patch("haystack.templatetags.more_like_this.SearchQuerySet")
class MoreLikeThisTagTestCase(TestCase):
    def render(self, template, context):
        # Why on Earth does Django not have a TemplateTestCase yet?
        t = Template(template)
        c = Context(context)
        return t.render(c)

    def test_more_like_this_without_limit(self, mock_sqs):
        mock_model = MockModel.objects.get(pk=3)
        template = """{% load more_like_this %}{% more_like_this entry as related_content %}{% for rc in related_content %}{{ rc.id }}{% endfor %}"""
        context = {'entry': mock_model}

        mlt = mock_sqs.return_value.more_like_this
        mlt.return_value = [{"id": "test_id"}]

        self.assertEqual("test_id", self.render(template, context))

        mlt.assert_called_once_with(mock_model)

    def test_more_like_this_with_limit(self, mock_sqs):
        mock_model = MockModel.objects.get(pk=3)
        template = """{% load more_like_this %}{% more_like_this entry as related_content limit 5 %}{% for rc in related_content %}{{ rc.id }}{% endfor %}"""
        context = {'entry': mock_model}

        mlt = mock_sqs.return_value.more_like_this
        mlt.return_value.__getitem__.return_value = [{"id": "test_id"}]

        self.assertEqual("test_id", self.render(template, context))

        mlt.assert_called_once_with(mock_model)

        mock_sqs.assert_has_calls([call().more_like_this(mock_model),
                                   call().more_like_this().__getitem__(slice(None, 5))],
                                   any_order=True)

    def test_more_like_this_for_model(self, mock_sqs):
        mock_model = MockModel.objects.get(pk=3)
        template = """{% load more_like_this %}{% more_like_this entry as related_content for "core.mock" limit 5 %}{% for rc in related_content %}{{ rc.id }}{% endfor %}"""
        context = {'entry': mock_model}

        self.render(template, context)

        mock_sqs.assert_has_calls([call().models().more_like_this(mock_model),
                                   call().models().more_like_this().__getitem__(slice(None, 5))],
                                   any_order=True)

    if django.get_version() == '1.7':
        # FIXME: https://github.com/toastdriven/django-haystack/issues/1069
        test_more_like_this_for_model = unittest.expectedFailure(test_more_like_this_for_model)
