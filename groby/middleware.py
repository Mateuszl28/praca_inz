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


class SecurityHeadersMiddleware:
    """Dodaje typowe security headers (CSP, HSTS, frame, referrer, permissions)."""

    CSP = (
        "default-src 'self'; "
        "img-src 'self' data: https: blob:; "
        "style-src 'self' 'unsafe-inline' https://unpkg.com https://fonts.googleapis.com https://cdn.jsdelivr.net; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "script-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net https://cdn.tailwindcss.com https://d3js.org; "
        "connect-src 'self' https://nominatim.openstreetmap.org; "
        "frame-ancestors 'self';"
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault('X-Content-Type-Options', 'nosniff')
        response.setdefault('X-Frame-Options', 'SAMEORIGIN')
        response.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.setdefault('Permissions-Policy',
                            'geolocation=(self), microphone=(self), camera=(self)')
        if request.is_secure():
            response.setdefault('Strict-Transport-Security',
                                'max-age=31536000; includeSubDomains')
        if not request.path.startswith('/admin'):
            response.setdefault('Content-Security-Policy', self.CSP)
        return response
