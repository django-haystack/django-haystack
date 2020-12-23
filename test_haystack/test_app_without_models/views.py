# encoding: utf-8
from django.http import HttpResponse


def simple_view(request):
    return HttpResponse("OK")
