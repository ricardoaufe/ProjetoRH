from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class CID(models.Model):
    code = models.CharField(max_length=10, unique=True, verbose_name='Código CID')
    description = models.CharField(max_length=500, verbose_name='Descrição Oficial')

    class Meta:
        verbose_name = 'CID-10'
        verbose_name_plural = 'CIDs-10'
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.description}"
    
class Occurrence(models.Model):
    employee = models.ForeignKey(
        'Employee',
        on_delete=models.CASCADE,
        related_name='occurrences',
        verbose_name='Funcionário',
    )
    title = models.CharField(max_length=100, verbose_name='Título')
    cid = models.ForeignKey(
        CID,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='occurrences',
        verbose_name='CID-10 (Opcional)'
    )
    description = models.TextField(verbose_name='Descrição')

    occurrence_date = models.DateField(verbose_name='Data da Ocorrência / Início')

    is_absence = models.BooleanField(
        default=False, 
        verbose_name='É um afastamento?'
    )
    end_date = models.DateField(
        blank=True, 
        null=True, 
        verbose_name='Data de Fim'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='occurrences_created',
        verbose_name='Criado por',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='occurrences_updated',
        verbose_name='Atualizado por',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Ocorrência'
        verbose_name_plural = 'Ocorrências'
        ordering = ['-occurrence_date', '-created_at']

    @property
    def absence_duration(self):
        """Calcula os dias de afastamento automaticamente."""
        if not self.is_absence:
            return 0

        final_date = self.end_date if self.end_date else timezone.localdate()

        delta = (final_date - self.occurrence_date).days + 1
        
        return max(0, delta)

    def clean(self):
        super().clean()

        if self.occurrence_date and self.occurrence_date > timezone.localdate():
            raise ValidationError({
                'occurrence_date': 'A data da ocorrência/início não pode ser no futuro.'
            })

        if self.is_absence and self.end_date and self.occurrence_date and self.end_date < self.occurrence_date:
            raise ValidationError({
                'end_date': 'A data de fim não pode ser anterior à data de início.'
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        tipo = "Afastamento" if self.is_absence else "Ocorrência"
        return f'{tipo}: {self.title} — {self.employee.name} ({self.occurrence_date})'


    