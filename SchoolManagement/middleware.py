from django.http import HttpResponseBadRequest

_CORRUPTED_CHARS = ('�', '\x00')


class RejectCorruptedPathMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if any(c in request.path for c in _CORRUPTED_CHARS):
            return HttpResponseBadRequest()
        return self.get_response(request)
