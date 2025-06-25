# aspectManager/models.py
import uuid
from django.db import models

def generate_id_aspect() -> str:
    return uuid.uuid4().hex[:10]

class Aspect(models.Model):
    id_aspect           = models.CharField(primary_key=True, max_length=10,
                                            default=generate_id_aspect,
                                            editable=False)
    name                = models.CharField("Nombre", max_length=100, unique=True)
    description         = models.TextField("Descripción", blank=True, null=True)
    weight              = models.DecimalField("Peso (%)", max_digits=5, decimal_places=2,
                                                blank=True, null=True)
    approved            = models.BooleanField("Aprobado", default=False)
    is_completed        = models.BooleanField(default=False)
    acceptance_criteria = models.TextField("Criterio de aceptación",
                                            blank=True, null=True)
    evaluation_rule     = models.TextField("Regla de evaluación",
                                            blank=True, null=True)

    trait = models.ForeignKey(
        "traitManager.Trait",
        on_delete=models.CASCADE,
        related_name="aspects",
        verbose_name="Característica"
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Aspecto"
        verbose_name_plural = "Aspectos"

    def __str__(self) -> str:
        return self.name
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("aspect_detail", kwargs={"pk": self.pk})