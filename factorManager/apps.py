# factorManager/apps.py
from django.apps import AppConfig

class FactormanagerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'factorManager'

    def ready(self):
        import factorManager.signals
