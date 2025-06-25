from django.apps import AppConfig


class AspectmanagerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'aspectManager'

def ready(self):
    from . import signals  # noqa
