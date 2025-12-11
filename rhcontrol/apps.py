from django.apps import AppConfig


class RhcontrolConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rhcontrol' # Nome do aplicativo

class RhcontrolConfig(RhcontrolConfig):
    def ready(self):
        import rhcontrol.signals 
