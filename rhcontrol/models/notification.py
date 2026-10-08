from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class EventTypes(models.TextChoices):
    VACATION_START = 'VACATION', 'Início de Férias'
    TRAINING_DUE = 'TRAINING', 'Vencimento de Treinamento'
    TRIAL_END = 'TRIAL_END', 'Fim do Contrato de Experiência'
    EXAM_DUE = 'EXAM_DUE', 'Exame Ocupacional a Vencer'

    BIRTHDAY = 'BIRTHDAY', 'Aniversário do Colaborador'
    COMPANY_ANNIVERSARY = 'COMPANY_ANNIVERSARY', 'Aniversário de Empresa'

    CAREER_PLAN_REMINDER = 'CAREER_PLAN_REMINDER', 'Aviso de Promoção'
    CAREER_PLAN_CANCELLED = 'CAREER_PLAN_CANCELLED', 'Plano de Carreira Cancelado'
    CAREER_PLAN_EFFECTIVE = 'CAREER_PLAN_EFFECTIVE', 'Promoção Efetivada'
    CONTRACT_END = 'CONTRACT_END', 'Fim de Contrato'

class NotificationRule(models.Model):

    event_type = models.CharField('Tipo de Evento', max_length=30, choices=EventTypes.choices)
    days_in_advance = models.PositiveIntegerField('Dias de Antecedência', default=15)
    is_active = models.BooleanField('Regra Ativa', default=True)

    class Meta:

        unique_together = ('event_type', 'days_in_advance')

    def __str__(self):
        return f"{self.get_event_type_display()} ({self.days_in_advance} dias)"

class NotificationRecipient(models.Model):
    name = models.CharField('Nome / Setor', max_length=100)
    email = models.EmailField('E-mail', unique=True)
    receive_all_events = models.BooleanField('Recebe Todos os Eventos', default=False)
    
    subscribed_rules = models.ManyToManyField(
        NotificationRule, 
        blank=True, 
        related_name='subscribers',
        verbose_name='Regras Inscritas'
    )
    is_active = models.BooleanField('Ativo', default=True)

    def __str__(self):
        return f"{self.name} <{self.email}>"

class NotificationLog(models.Model):

    rule = models.ForeignKey(NotificationRule, on_delete=models.PROTECT, related_name='logs')
    employee = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name='notifications')

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    related_object = GenericForeignKey('content_type', 'object_id')

    reference_year = models.PositiveIntegerField('Ano de Referência do Evento')

    recipients_snapshot = models.JSONField(
        'Destinatários (Snapshot)', 
        default=list, 
        help_text="Lista exata de e-mails que receberam esta notificação no momento do envio."
    )
    
    sent_at = models.DateTimeField('Enviado em', auto_now_add=True)

    class Meta:
        unique_together = ('rule', 'content_type', 'object_id', 'reference_year')
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['reference_year']),
        ]

    def __str__(self):
        return f"Log: {self.rule.event_type} - {self.employee.name} ({self.reference_year})"
    

class UserAlertPreference(models.Model):

    ALERT_CHOICES = [
        ('vacation_start', 'Início de Férias'),
        ('training_due', 'Vencimento de Treinamento'),
        ('trial_end', 'Fim do Contrato de Experiência'),
        ('exam_due', 'Exame Ocupacional a Vencer'),
        ('birthday', 'Aniversário do Colaborador'),
        ('company_anniversary', 'Aniversário de Empresa'),
        ('career_plan_reminder', 'Aviso de Promoção'),
        ('career_plan_cancelled', 'Plano de Carreira Cancelado'),
        ('career_plan_effective', 'Promoção Efetivada'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='alert_preferences')
    alert_type = models.CharField(max_length=30, choices=ALERT_CHOICES)

    class Meta:
        unique_together = ('user', 'alert_type')

    def __str__(self):
        return f"{self.user.username} - {self.get_alert_type_display()}"