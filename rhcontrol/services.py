import logging
from datetime import date, timedelta
from django.core import mail
from django.utils import timezone
from .models import Employee, EventTypes, NotificationRule, Vacation, Training, NotificationRecipient, NotificationLog, CareerPlan
from django.db.models import Q, QuerySet
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

def get_active_recipients_queryset_for_rule(rule) -> QuerySet:
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
    
    subject = event.get('custom_subject') or f"Aviso RH: {event_name_display} - {employee.name}"
    body = event.get('custom_body') or (
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


def notify_career_plan_event(plan: CareerPlan, event_type: str, dry_run: bool = False) -> None:
    """
    Constrói o dicionário padrão de evento e dispara o e-mail usando a infraestrutura existente.
    Fail-safe: Se a regra não existir, apenas loga e aborta.
    """
    rule = NotificationRule.objects.filter(event_type=event_type, is_active=True).first()
    
    if not rule:
        logger.warning(f"Sem regra ativa configurada para [{event_type}]. E-mail não enviado para {plan.employee.name}.")
        return
    
    subject = f"Aviso RH: {rule.get_event_type_display()} - {plan.employee.name}"
    body = (
        f"Olá,\n\n"
        f"Aviso do Módulo de Plano de Carreira:\n\n"
        f"Colaborador: {plan.employee.name}\n"
        f"Próximo Cargo: {plan.proposed_job.name}\n"
        f"Data da Promoção: {plan.promotion_date.strftime('%d/%m/%Y')}\n"
        f"Status Atualizado: {plan.get_status_display()}\n"
    )
    if plan.cancellation_reason:
        body += f"Motivo do Cancelamento: {plan.cancellation_reason}\n"
        
    body += "\nPor favor, acesse o sistema para mais detalhes."

    event_dict = {
        'event_type': event_type,
        'rule': rule,
        'employee': plan.employee,
        'related_object': plan,
        'event_date': plan.promotion_date,
        'reference_year': plan.promotion_date.year,
        'custom_subject': subject,
        'custom_body': body,
    }

    send_notification_for_event(event_dict, dry_run=dry_run)


def process_career_plans(dry_run: bool = False) -> None:
    """
    Motor diário de transições de status do Plano de Carreira.
    Roda via Hub (run_automations).
    """
    today = timezone.localdate()
    if dry_run:
        logger.info(f"=== [DRY-RUN] Iniciando simulação de Planos de Carreira para {today} ===")
    else:
        logger.info(f"=== Iniciando processamento de Planos de Carreira para {today} ===")

    plans_to_cancel_dismissed = CareerPlan.objects.filter(
        status__in=[CareerPlan.PlanStatus.SCHEDULED, CareerPlan.PlanStatus.AWAITING_CONFIRMATION, CareerPlan.PlanStatus.CONFIRMED],
        employee__termination_date__isnull=False,
        employee__termination_date__lte=today
    )
    for plan in plans_to_cancel_dismissed:
        if dry_run:
            logger.info(f"[DRY-RUN] Cancelaria plano de [{plan.employee.name}] (Motivo: Funcionário desligado).")
        else:
            plan.status = CareerPlan.PlanStatus.CANCELLED
            plan.cancellation_reason = 'Funcionário desligado'
            plan.save(update_fields=['status', 'cancellation_reason', 'updated_at'])
            notify_career_plan_event(plan, EventTypes.CAREER_PLAN_CANCELLED)

    scheduled_plans = CareerPlan.objects.filter(status=CareerPlan.PlanStatus.SCHEDULED)
    for plan in scheduled_plans:
        window_start = plan.promotion_date - timedelta(days=30)

        if today >= plan.promotion_date:
            if dry_run:
                logger.info(f"[DRY-RUN] Cancelaria plano de [{plan.employee.name}] (Motivo: Janela perdida/cron inativo).")
            else:
                plan.status = CareerPlan.PlanStatus.CANCELLED
                plan.cancellation_reason = 'Janela perdida/cron inativo'
                plan.save(update_fields=['status', 'cancellation_reason', 'updated_at'])
                notify_career_plan_event(plan, EventTypes.CAREER_PLAN_CANCELLED)

        elif today >= window_start and plan.reminder_sent_at is None:
            if dry_run:
                logger.info(f"[DRY-RUN] Mudaria status de [{plan.employee.name}] para AWAITING_CONFIRMATION e enviaria aviso.")
            else:
                plan.status = CareerPlan.PlanStatus.AWAITING_CONFIRMATION
                plan.reminder_sent_at = timezone.now()
                plan.save(update_fields=['status', 'reminder_sent_at', 'updated_at'])
                notify_career_plan_event(plan, EventTypes.CAREER_PLAN_REMINDER)

    expired_plans = CareerPlan.objects.filter(
        status=CareerPlan.PlanStatus.AWAITING_CONFIRMATION,
        promotion_date__lte=today
    )
    for plan in expired_plans:
        if dry_run:
            logger.info(f"[DRY-RUN] Cancelaria plano de [{plan.employee.name}] (Motivo: Prazo expirado sem confirmação do RH).")
        else:
            plan.status = CareerPlan.PlanStatus.CANCELLED
            plan.cancellation_reason = 'Prazo de confirmação expirado'
            plan.save(update_fields=['status', 'cancellation_reason', 'updated_at'])
            notify_career_plan_event(plan, EventTypes.CAREER_PLAN_CANCELLED)

    dia_d_plans = CareerPlan.objects.filter(
        status=CareerPlan.PlanStatus.CONFIRMED,
        promotion_date__lte=today,
        effective_applied_at__isnull=True
    )
    for plan in dia_d_plans:
        employee = plan.employee

        if plan.proposed_job.department != employee.department:
            if dry_run:
                logger.info(f"[DRY-RUN] Cancelaria plano de [{employee.name}] (Conflito: Setor alterado manualmente).")
            else:
                plan.status = CareerPlan.PlanStatus.CANCELLED
                plan.cancellation_reason = 'Conflito: Setor alterado manualmente antes da promoção'
                plan.save(update_fields=['status', 'cancellation_reason', 'updated_at'])
                notify_career_plan_event(plan, EventTypes.CAREER_PLAN_CANCELLED)
            continue
            
        if dry_run:
            logger.info(f"[DRY-RUN] Efetivaria promoção de [{employee.name}] para o cargo [{plan.proposed_job.name}]. Salvaria histórico.")
        else:
            try:
                with transaction.atomic():
                    employee.job_title = plan.proposed_job
                    employee.department = plan.proposed_job.department
                    employee.current_salary = plan.proposed_salary
                    employee.save(update_fields=['job_title', 'current_salary'])
                    
                    plan.status = CareerPlan.PlanStatus.EFFECTIVE
                    plan.effective_applied_at = timezone.now()
                    plan.save(update_fields=['status', 'effective_applied_at', 'updated_at'])

                notify_career_plan_event(plan, EventTypes.CAREER_PLAN_EFFECTIVE)
                logger.info(f"Promoção de [{employee.name}] efetivada com sucesso.")
            except Exception as e:
                logger.error(f"Falha crítica ao efetivar promoção do plano {plan.id}: {str(e)}")

    if dry_run:
        logger.info("=== [DRY-RUN] Finalizado ===")