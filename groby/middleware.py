from .signals import ustaw_uzytkownika


class BiezacyUzytkownikMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ustaw_uzytkownika(getattr(request, 'user', None))
        try:
            return self.get_response(request)
        finally:
            ustaw_uzytkownika(None)
