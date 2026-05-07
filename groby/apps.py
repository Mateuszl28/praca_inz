from django.apps import AppConfig


class GrobyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'groby'

    def ready(self):
        from . import signals  # noqa: F401
