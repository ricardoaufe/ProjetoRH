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
            # NOTE: Training model does not have a 'due_date' or per-employee FK.
            # This handler is intentionally left as a no-op until those fields are added.
            pass

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


# ═══════════════════════════════════════════════════════════════════════════════
#
#  UPCOMING EVENTS ENGINE
#  ──────────────────────
#  Centralized service that aggregates "upcoming events" across all HR models
#  for use in the dashboard card, filtered events page, and future analytics.
#
#  HOW TO ADD A NEW CATEGORY
#  ─────────────────────────
#  1. Choose a category name string (e.g. "MEDICAL_EXAM_DUE").
#  2. Write a private generator:
#         def _ue_generate_<category>(start, end, filters) -> list[dict]
#     Use _ue_append() to build each dict, _ue_in_range() to test dates.
#  3. Register it in _UE_GENERATORS at the bottom of this section.
#  4. Done — get_upcoming_events() calls all registered generators automatically.
#
# ═══════════════════════════════════════════════════════════════════════════════

import calendar as _calendar
from typing import Optional as _Optional

_UE_MAX_RANGE    = 180
_UE_DEFAULT_DAYS = 30
_UE_MAX_LIMIT    = 500
_UE_REMINDER_DAYS = 30   # days before promotion_date to generate CAREER_PLAN_REMINDER_WINDOW

_UE_ACTIVE_CAREER_STATUSES = {
    CareerPlan.PlanStatus.SCHEDULED,
    CareerPlan.PlanStatus.AWAITING_CONFIRMATION,
    CareerPlan.PlanStatus.CONFIRMED,
    CareerPlan.PlanStatus.EFFECTIVE,
    CareerPlan.PlanStatus.CANCELLED,
}

# ── Category metadata: icon / pill CSS class / human label ─────
# Add one entry here whenever you register a new category.

_UE_CATEGORY_META: dict[str, dict] = {
    "BIRTHDAY":                      {"icon": "fa-birthday-cake",        "pill_class": "birthday",                      "category_label": "Aniversário"},
    "COMPANY_ANNIVERSARY":           {"icon": "fa-building",             "pill_class": "company_anniversary",           "category_label": "Aniversário de Empresa"},
    "VACATION_START":                {"icon": "fa-umbrella-beach",       "pill_class": "vacation_start",                "category_label": "Início de Férias"},
    "VACATION_RETURN":               {"icon": "fa-plane-arrival",        "pill_class": "vacation_return",               "category_label": "Retorno de Férias"},
    "TRAINING_DATE":                 {"icon": "fa-chalkboard-teacher",   "pill_class": "training_date",                 "category_label": "Treinamento"},
    "CAREER_PLAN_PROMOTION_DATE":    {"icon": "fa-chart-line",           "pill_class": "career_plan_promotion_date",    "category_label": "Promoção"},
    "CAREER_PLAN_REMINDER_WINDOW":   {"icon": "fa-chart-line",           "pill_class": "career_plan_reminder_window",   "category_label": "Aviso de Promoção (30d)"},
    "TRIAL_60_WARNING":              {"icon": "fa-exclamation-triangle",  "pill_class": "trial_60_warning",              "category_label": "Contrato (60 dias)"},
    "TRIAL_90_WARNING":              {"icon": "fa-exclamation-triangle",  "pill_class": "trial_90_warning",              "category_label": "Contrato (90 dias)"},
}
_UE_META_FALLBACK = {"icon": "fa-calendar", "pill_class": "default", "category_label": "Evento"}


# ── Low-level helpers ───────────────────────────────────────────

def _ue_clamp(start: _Optional[date], end: _Optional[date]) -> tuple[date, date]:
    """Enforce default and maximum date range."""
    today = timezone.localdate()
    if start is None:
        start = today
    if end is None:
        end = start + timedelta(days=_UE_DEFAULT_DAYS)
    if (end - start).days > _UE_MAX_RANGE:
        end = start + timedelta(days=_UE_MAX_RANGE)
    return start, end


def _ue_in_range(d: date, start: date, end: date) -> bool:
    return start <= d <= end


def _ue_append(
    events: list,
    *,
    date:            date,
    category:        str,
    title:           str,
    object_type:     str,
    object_id:       int,
    status:          str           = "PENDING",
    employee_id:     _Optional[int] = None,
    employee_name:   _Optional[str] = None,
    department_name: _Optional[str] = None,
    email_event:     bool           = False,
    requires_action: bool           = False,
) -> None:
    meta = _UE_CATEGORY_META.get(category, _UE_META_FALLBACK)
    events.append({
        "date":            date,
        "category":        category,
        "title":           title,
        "employee_id":     employee_id,
        "employee_name":   employee_name,
        "department_name": department_name,
        "object_type":     object_type,
        "object_id":       object_id,
        "status":          status,
        "email_event":     email_event,
        "requires_action": requires_action,
        # ── Template helpers (Fix C) ──────────────────────────
        "icon":            meta["icon"],
        "pill_class":      meta["pill_class"],
        "category_label":  meta["category_label"],
    })


def _ue_next_annual(ref: date, start: date, end: date) -> _Optional[date]:
    """
    Return the next occurrence of a recurring annual date (birthday, anniversary)
    that falls within [start, end]. Handles Feb-29 gracefully.
    """
    m, d = ref.month, ref.day
    for year in range(start.year, end.year + 1):
        safe_d = min(d, _calendar.monthrange(year, m)[1])
        try:
            occ = date(year, m, safe_d)
        except ValueError:
            continue
        if _ue_in_range(occ, start, end):
            return occ
    return None


# ── Event generators ────────────────────────────────────────────

def _ue_generate_birthday(start: date, end: date, filters: dict) -> list[dict]:
    events: list[dict] = []
    qs = Employee.objects.select_related("department").filter(
        termination_date__isnull=True, birth_date__isnull=False
    )
    if filters.get("employee_id"):
        qs = qs.filter(pk=filters["employee_id"])
    if filters.get("department_id"):
        qs = qs.filter(department_id=filters["department_id"])

    for emp in qs:
        occ = _ue_next_annual(emp.birth_date, start, end)
        if occ is None:
            continue
        age = occ.year - emp.birth_date.year
        _ue_append(
            events,
            date=occ, category="BIRTHDAY",
            title=f"Aniversário de {emp.name} ({age} anos)",
            object_type="employee", object_id=emp.pk,
            employee_id=emp.pk, employee_name=emp.name,
            department_name=emp.department.name if emp.department_id else None,
            email_event=True,
        )
    return events


def _ue_generate_company_anniversary(start: date, end: date, filters: dict) -> list[dict]:
    events: list[dict] = []
    qs = Employee.objects.select_related("department").filter(
        termination_date__isnull=True, hire_date__isnull=False
    )
    if filters.get("employee_id"):
        qs = qs.filter(pk=filters["employee_id"])
    if filters.get("department_id"):
        qs = qs.filter(department_id=filters["department_id"])

    for emp in qs:
        occ = _ue_next_annual(emp.hire_date, start, end)
        if occ is None:
            continue
        years = occ.year - emp.hire_date.year
        _ue_append(
            events,
            date=occ, category="COMPANY_ANNIVERSARY",
            title=f"{emp.name} — {years} ano{'s' if years != 1 else ''} de empresa",
            object_type="employee", object_id=emp.pk,
            employee_id=emp.pk, employee_name=emp.name,
            department_name=emp.department.name if emp.department_id else None,
            email_event=True,
        )
    return events


def _ue_generate_vacations(start: date, end: date, filters: dict) -> list[dict]:
    events: list[dict] = []

    # Two separate queries then deduplicated via distinct() on union
    qs = (
        Vacation.objects.select_related("employee", "employee__department")
        .filter(start_date__range=(start, end))
        | Vacation.objects.select_related("employee", "employee__department")
        .filter(return_date__range=(start, end))
    ).distinct()

    if filters.get("employee_id"):
        qs = qs.filter(employee_id=filters["employee_id"])
    if filters.get("department_id"):
        qs = qs.filter(employee__department_id=filters["department_id"])

    for vac in qs:
        emp  = vac.employee
        dept = emp.department.name if emp.department_id else None

        if vac.start_date and _ue_in_range(vac.start_date, start, end):
            _ue_append(
                events,
                date=vac.start_date, category="VACATION_START",
                title=f"Início de férias — {emp.name}",
                object_type="vacation", object_id=vac.pk,
                employee_id=emp.pk, employee_name=emp.name, department_name=dept,
            )

        if vac.return_date and _ue_in_range(vac.return_date, start, end):
            _ue_append(
                events,
                date=vac.return_date, category="VACATION_RETURN",
                title=f"Retorno de férias — {emp.name}",
                object_type="vacation", object_id=vac.pk,
                employee_id=emp.pk, employee_name=emp.name, department_name=dept,
            )
    return events


def _ue_generate_trainings(start: date, end: date, filters: dict) -> list[dict]:
    events: list[dict] = []
    qs = Training.objects.filter(start_date__range=(start, end))

    if filters.get("department_id"):
        qs = qs.filter(target_department_id=filters["department_id"])
    if filters.get("employee_id"):
        qs = qs.filter(scheduled_employees__pk=filters["employee_id"])

    for t in qs:
        _ue_append(
            events,
            date=t.start_date, category="TRAINING_DATE",
            title=f"Treinamento: {t.training_name}",
            object_type="training", object_id=t.pk,
            department_name=t.target_department.name if t.target_department_id else None,
            email_event=True,
        )
    return events


def _ue_generate_career_plans(start: date, end: date, filters: dict) -> list[dict]:
    events: list[dict] = []

    # ── Promotion date events ─────────────────────────────────────
    promo_qs = (
        CareerPlan.objects
        .select_related("employee", "employee__department", "proposed_job")
        .filter(promotion_date__range=(start, end), status__in=_UE_ACTIVE_CAREER_STATUSES)
    )

    # ── Reminder window: (promotion_date - 30d) falls in [start, end]
    #    ⟹  promotion_date ∈ [start+30, end+30]
    r_start = start + timedelta(days=_UE_REMINDER_DAYS)
    r_end   = end   + timedelta(days=_UE_REMINDER_DAYS)
    reminder_qs = (
        CareerPlan.objects
        .select_related("employee", "employee__department", "proposed_job")
        .filter(
            promotion_date__range=(r_start, r_end),
            status__in={
                CareerPlan.PlanStatus.SCHEDULED,
                CareerPlan.PlanStatus.AWAITING_CONFIRMATION,
                CareerPlan.PlanStatus.CONFIRMED,
            },
        )
    )

    for qs, extra_filter in ((promo_qs, True), (reminder_qs, True)):
        if filters.get("employee_id"):
            qs = qs.filter(employee_id=filters["employee_id"])
        if filters.get("department_id"):
            qs = qs.filter(employee__department_id=filters["department_id"])
        if filters.get("status"):
            qs = qs.filter(status=filters["status"])

        if qs is promo_qs:
            for plan in qs:
                emp  = plan.employee
                dept = emp.department.name if emp.department_id else None
                _ue_append(
                    events,
                    date=plan.promotion_date, category="CAREER_PLAN_PROMOTION_DATE",
                    title=f"Promoção de {emp.name} → {plan.proposed_job.name} ({plan.get_status_display()})",
                    object_type="careerplan", object_id=plan.pk,
                    status=plan.status,
                    employee_id=emp.pk, employee_name=emp.name, department_name=dept,
                    email_event=True,
                    requires_action=(plan.status == CareerPlan.PlanStatus.AWAITING_CONFIRMATION),
                )
        else:
            for plan in qs:
                emp  = plan.employee
                dept = emp.department.name if emp.department_id else None
                reminder_date = plan.promotion_date - timedelta(days=_UE_REMINDER_DAYS)
                if not _ue_in_range(reminder_date, start, end):
                    continue
                _ue_append(
                    events,
                    date=reminder_date, category="CAREER_PLAN_REMINDER_WINDOW",
                    title=f"Aviso: promoção de {emp.name} em {plan.promotion_date.strftime('%d/%m/%Y')} (30 dias)",
                    object_type="careerplan", object_id=plan.pk,
                    status=plan.status,
                    employee_id=emp.pk, employee_name=emp.name, department_name=dept,
                    email_event=True, requires_action=True,
                )
    return events


def _ue_generate_trial(start: date, end: date, filters: dict) -> list[dict]:
    """
    TRIAL_60_WARNING / TRIAL_90_WARNING — 5 days before each trial milestone.

    Reverse-engineer the hire_date window instead of scanning all employees:
        warning_date = hire_date + milestone - 5
        hire_date    = warning_date - milestone + 5
        If warning_date ∈ [start, end] → hire_date ∈ [start - milestone + 5, end - milestone + 5]
    """
    events: list[dict] = []
    WARNING_OFFSET = 5

    milestones = [
        (60, "TRIAL_60_WARNING",  "Fim do 1º período de experiência (60 dias) — {name}"),
        (90, "TRIAL_90_WARNING",  "Fim do contrato de experiência (90 dias) — {name}"),
    ]

    for days, category, title_tpl in milestones:
        hire_start = start - timedelta(days=days - WARNING_OFFSET)
        hire_end   = end   - timedelta(days=days - WARNING_OFFSET)

        qs = Employee.objects.select_related("department").filter(
            is_trial_contract=True,
            hire_date__range=(hire_start, hire_end),
            termination_date__isnull=True,
        )
        if filters.get("employee_id"):
            qs = qs.filter(pk=filters["employee_id"])
        if filters.get("department_id"):
            qs = qs.filter(department_id=filters["department_id"])

        for emp in qs:
            warning_date = emp.hire_date + timedelta(days=days - WARNING_OFFSET)
            if not _ue_in_range(warning_date, start, end):
                continue
            _ue_append(
                events,
                date=warning_date, category=category,
                title=title_tpl.format(name=emp.name),
                object_type="employee", object_id=emp.pk,
                employee_id=emp.pk, employee_name=emp.name,
                department_name=emp.department.name if emp.department_id else None,
                email_event=True, requires_action=True,
            )
    return events


# ── Generator registry ──────────────────────────────────────────
# Maps frozenset(categories_produced) → generator_function.
# Add new generators here — no other code changes needed.

_UE_GENERATORS = {
    frozenset({"BIRTHDAY"}):                              _ue_generate_birthday,
    frozenset({"COMPANY_ANNIVERSARY"}):                   _ue_generate_company_anniversary,
    frozenset({"VACATION_START", "VACATION_RETURN"}):     _ue_generate_vacations,
    frozenset({"TRAINING_DATE"}):                         _ue_generate_trainings,
    frozenset({
        "CAREER_PLAN_PROMOTION_DATE",
        "CAREER_PLAN_REMINDER_WINDOW",
    }):                                                   _ue_generate_career_plans,
    frozenset({"TRIAL_60_WARNING", "TRIAL_90_WARNING"}):  _ue_generate_trial,
}


# ── Public API ──────────────────────────────────────────────────

def get_upcoming_events(
    start_date:        _Optional[date] = None,
    end_date:          _Optional[date] = None,
    categories:        _Optional[list[str]] = None,
    only_email_events: bool = False,
    employee_id:       _Optional[int] = None,
    department_id:     _Optional[int] = None,
    status:            _Optional[str] = None,
    limit:             int = 200,
) -> list[dict]:
    """
    Return a sorted list of upcoming HR event dicts.

    Parameters
    ----------
    start_date        : Range start (defaults to today).
    end_date          : Range end (defaults to start + 30 days; max 180 days).
    categories        : Whitelist of category strings. None = all categories.
    only_email_events : Return only events where email_event=True.
    employee_id       : Filter to a single employee.
    department_id     : Filter to a single department.
    status            : Filter career plan events by status value.
    limit             : Max results (hard cap: 500).

    Returns
    -------
    list[dict] sorted by (date, category), each dict has:
        date, category, title, employee_id, employee_name,
        department_name, object_type, object_id, status,
        email_event, requires_action
    """
    start, end = _ue_clamp(start_date, end_date)
    limit = min(limit, _UE_MAX_LIMIT)

    filters = {
        "employee_id":   employee_id,
        "department_id": department_id,
        "status":        status,
    }

    requested = set(categories) if categories else None
    events: list[dict] = []

    for category_set, generator_fn in _UE_GENERATORS.items():
        if requested is not None and category_set.isdisjoint(requested):
            continue
        events.extend(generator_fn(start, end, filters))

    # Post-generation filters
    if requested:
        events = [e for e in events if e["category"] in requested]
    if only_email_events:
        events = [e for e in events if e["email_event"]]

    events.sort(key=lambda e: (e["date"], e["category"]))
    return events[:limit]
