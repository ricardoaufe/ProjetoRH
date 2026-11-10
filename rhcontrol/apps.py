from django.apps import AppConfig


class RhcontrolConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rhcontrol'  # Nome do aplicativo

    def ready(self):
        from . import signals  # noqa: F401  (registra os receivers)
