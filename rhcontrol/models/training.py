from django.core.exceptions import ValidationError
from django.db import models


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