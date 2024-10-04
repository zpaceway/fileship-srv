import json
from django.http.request import HttpRequest


def submission(request: HttpRequest):
    raw = {**request.POST.dict(), **request.GET.dict()}

    try:
        raw = {**raw, **json.loads(request.body.decode())}
    except:
        pass

    return raw
