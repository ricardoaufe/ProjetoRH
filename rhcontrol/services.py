import logging
from datetime import date, timedelta
from django.utils import timezone
from .models import Employee, EventTypes, NotificationRule, Vacation, Training, NotificationRecipient, NotificationLog
from django.db.models import Q
from rhcontrol import models
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import transaction, IntegrityError

def get_events_for_notification() -> list[dict]:
    """
    Iterates through active notification rules, calculates the target date based on
    the advance notice of each rule, and returns a standardized list of events.
    """
    today = timezone.localdate()
    events_to_notify = []

    active_rules = NotificationRule.objects.filter(is_active=True)

    for rule in active_rules:

        target_date = today + timedelta(days=rule.days_in_advance)
        
        if rule.event_type == EventTypes.BIRTHDAY:
            employees = Employee.objects.filter(
                birth_date__month=target_date.month,
                birth_date__day=target_date.day,
                termination_date__isnull=True
            )
            for emp in employees:
                events_to_notify.append({
                    'event_type': rule.event_type,
                    'rule': rule,
                    'employee': emp,
                    'related_object': emp,
                    'event_date': date(target_date.year, target_date.month, target_date.day),
                    'reference_year': target_date.year
                })

        elif rule.event_type == EventTypes.COMPANY_ANNIVERSARY:
            employees = Employee.objects.filter(
                hire_date__month=target_date.month,
                hire_date__day=target_date.day,
                termination_date__isnull=True
            )
            for emp in employees:
                events_to_notify.append({
                    'event_type': rule.event_type,
                    'rule': rule,
                    'employee': emp,
                    'related_object': emp,
                    'event_date': date(target_date.year, target_date.month, target_date.day),
                    'reference_year': target_date.year
                })

        elif rule.event_type == EventTypes.VACATION_START:
            vacations = Vacation.objects.filter(
                start_date=target_date
            ).select_related('employee')
            
            for vacation in vacations:
                events_to_notify.append({
                    'event_type': rule.event_type,
                    'rule': rule,
                    'employee': vacation.employee,
                    'related_object': vacation,
                    'event_date': vacation.start_date,
                    'reference_year': vacation.start_date.year
                })

        elif rule.event_type == EventTypes.TRAINING_DUE:
            trainings = Training.objects.filter(
                due_date=target_date
            ).select_related('employee')
            
            for training in trainings:
                events_to_notify.append({
                    'event_type': rule.event_type,
                    'rule': rule,
                    'employee': training.employee,
                    'related_object': training,
                    'event_date': training.due_date,
                    'reference_year': training.due_date.year
                })
        
    return events_to_notify

def get_active_recipients_queryset_for_rule(rule) -> models.QuerySet:
    """
    Returns the QuerySet of active recipients who should receive a specific rule.
    A recipient is included if:
    1. is_active=True AND (receive_all_events=True OR the rule is in subscribed_rules)
    """
    return NotificationRecipient.objects.filter(
        Q(is_active=True) & 
        (Q(receive_all_events=True) | Q(subscribed_rules=rule))
    ).distinct()


def get_recipients_for_event(event: dict) -> list[str]:
    """
    Processes the event dictionary (generated in Step 2) and returns a flat,
    unique list of emails that should receive the notification.
    """
    rule = event.get('rule')

    if not rule:
        return []

    recipients_qs = get_active_recipients_queryset_for_rule(rule)

    raw_emails = recipients_qs.values_list('email', flat=True)

    unique_emails = list({email.strip().lower() for email in raw_emails if email})
    
    return unique_emails





logger = logging.getLogger(__name__)

def process_notifications(dry_run: bool = False) -> None:
    """
    Função orquestradora: Busca todos os eventos pendentes e processa individualmente.
    Resiliente: O erro de um evento não interrompe o fluxo dos demais.
    """
    events = get_events_for_notification()
    
    if not events:
        logger.info("Nenhum evento pendente para notificação hoje.")
        return

    for event in events:
        try:
            send_notification_for_event(event, dry_run=dry_run)
        except Exception as e:
            event_name = event.get('rule').get_event_type_display() if event.get('rule') else 'Desconhecido'
            emp_name = event.get('employee').name if event.get('employee') else 'Desconhecido'
            logger.error(f"Falha ao processar evento [{event_name}] para [{emp_name}]: {str(e)}")

def send_notification_for_event(event: dict, dry_run: bool = False) -> None:
    """
    Tenta registrar o log atomicamente. Se conseguir, envia o e-mail.
    Se falhar por concorrência (IntegrityError), aborta em silêncio (já foi enviado).
    """
    rule = event['rule']
    employee = event['employee']
    related_object = event['related_object']
    event_date = event['event_date']
    reference_year = event['reference_year']

    recipients_list = get_recipients_for_event(event)
    
    if not recipients_list:
        logger.info(f"Ignorado: Sem destinatários ativos para a regra [{rule.get_event_type_display()}].")
        return

    snapshot_ordenado = sorted(recipients_list)

    content_type = ContentType.objects.get_for_model(related_object, for_concrete_model=True)
    object_id = related_object.pk

    event_name_display = rule.get_event_type_display()
    formatted_date = event_date.strftime("%d/%m/%Y")
    
    subject = f"Aviso RH: {event_name_display} - {employee.name}"
    body = (
        f"Olá,\n\n"
        f"Este é um aviso automático do sistema de RH.\n\n"
        f"Evento: {event_name_display}\n"
        f"Colaborador: {employee.name}\n"
        f"Data da Ocorrência: {formatted_date}\n\n"
        f"Por favor, tome as providências necessárias."
    )

    if dry_run:
        already_sent = NotificationLog.objects.filter(
            rule=rule,
            content_type=content_type,
            object_id=object_id,
            reference_year=reference_year
        ).exists()

        if already_sent:
            logger.debug(f"[DRY-RUN] Já enviado anteriormente para [{employee.name}] - Ano {reference_year}, ignorado.")
        else:
            logger.info(f"[DRY-RUN] Simulação: Enviaria [{event_name_display}] para {len(snapshot_ordenado)} e-mail(s): {snapshot_ordenado}")
        
        return

    try:
        with transaction.atomic():
            NotificationLog.objects.create(
                rule=rule,
                employee=employee,
                content_type=content_type,
                object_id=object_id,
                reference_year=reference_year,
                recipients_snapshot=snapshot_ordenado
            )
            
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=snapshot_ordenado,
                fail_silently=False, 
            )
            
    except IntegrityError:
        logger.debug(f"Idempotência: Outro processo já enviou/está enviando [{event_name_display}] para [{employee.name}] - Ano {reference_year}.")
        return

    except Exception:
        raise

    logger.info(f"Sucesso: Notificação de [{event_name_display}] enviada e registrada para {len(snapshot_ordenado)} e-mail(s) sobre [{employee.name}].")