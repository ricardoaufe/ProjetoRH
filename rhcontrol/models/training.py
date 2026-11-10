import os
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Training(models.Model):
    training_name = models.CharField(max_length=200, verbose_name="Nome do Treinamento")
    start_date = models.DateField(verbose_name="Data de Início", blank=True, null=True)
    end_date = models.DateField(blank=True, null=True, verbose_name="Data de Fim")

    training_provider = models.CharField(max_length=200, blank=True, null=True, verbose_name="Fornecedor do Treinamento")
    LOCAL_CHOICES = [
        ('Interno', 'Interno'),
        ('Externo', 'Externo'),
    ]
    training_location_type = models.CharField(
        max_length=10, 
        choices=LOCAL_CHOICES, 
        default='Interno', 
        verbose_name="Local do Treinamento"
    )
    training_total_hours = models.IntegerField(help_text='Duração em horas', verbose_name="Duração (horas)")
    training_description = models.TextField(blank=True, null=True, verbose_name="Descrição do Treinamento")

    is_fundamental = models.BooleanField(default=False, verbose_name="É Treinamento Fundamental?")
    is_integration = models.BooleanField(
        default=False, 
        verbose_name="Treinamento de Integração (Onboarding)?",
        help_text="Marque se este treinamento é padrão para novos funcionários."
    )
    is_on_the_job = models.BooleanField(
        default=False,
        verbose_name="Treinamento On The Job?",
        help_text="Treinamento prático, no posto de trabalho.",
    )
    target_department = models.ForeignKey('Department', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Setor Alvo (Se Fundamental)")
    
    scheduled_employees = models.ManyToManyField('Employee', related_name='scheduled_trainings', blank=True, verbose_name="Funcionários Previstos")
    attended_employees = models.ManyToManyField('Employee', related_name='attended_trainings', blank=True, verbose_name="Funcionários Que Compareceram")

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({
                'end_date': 'A data de término não pode ser anterior à data de início.'
            })

    def __str__(self):
        return f'Treinamento: {self.training_name} em {self.start_date}'


def training_document_path(instance, filename):
    """Guarda com nome aleatório: o nome original fica só no banco."""
    ext = os.path.splitext(filename)[1].lower()
    return f"trainings/{timezone.localdate():%Y/%m}/{uuid4().hex}{ext}"


class TrainingDocument(models.Model):
    training = models.ForeignKey(
        Training,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name="Treinamento",
    )
    file = models.FileField(upload_to=training_document_path, verbose_name="Arquivo")
    original_name = models.CharField(max_length=255, verbose_name="Nome Original")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Enviado em")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Enviado por",
    )

    class Meta:
        verbose_name = "Documento do Treinamento"
        verbose_name_plural = "Documentos do Treinamento"
        ordering = ['uploaded_at']

    def __str__(self):
        return self.original_name
