from django.db import models
from django.conf import settings

class Event(models.Model):
    id = models.BigAutoField(primary_key=True)

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    date = models.DateField()
    time = models.TimeField()
    location = models.CharField(max_length=255, blank=True, null=True)
    link = models.URLField(blank=True, null=True)
    meeting_type = models.CharField(
        max_length=10,
        choices=[('Presencial','Presencial'), ('Virtual','Virtual')],
    )
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='event_participants'
    )
 
    def __str__(self):
        return f"{self.title} - {self.date}"