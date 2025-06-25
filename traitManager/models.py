# traitManager/models.py
import uuid
from django.db import models
from factorManager.models import Factor

def generate_id_trait() -> str:
    return uuid.uuid4().hex[:10]

class Trait(models.Model):
    id_trait    = models.CharField(primary_key=True, max_length=10,
                                    default=generate_id_trait,
                                    editable=False)
    name        = models.CharField("Nombre", max_length=100, unique=True)
    description = models.TextField("Descripción", blank=True, null=True)

    factor = models.ForeignKey(
        Factor,
        on_delete=models.CASCADE,
        related_name='traits',
        verbose_name='Factor Asociado'
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Característica"
        verbose_name_plural = "Características"

    def __str__(self):
        return self.name

    @property
    def approved_percentage(self) -> int:
        total = self.aspects.count()
        if total == 0:
            return 0
        approved = self.aspects.filter(approved=True).count()
        return int(approved * 100 / total)

    # navegación genérica
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("trait_detail", args=[str(self.pk)])
