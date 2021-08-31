from django.http import HttpResponse


def simple_view(request):
    return HttpResponse("OK")
