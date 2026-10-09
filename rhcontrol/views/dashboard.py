from datetime import date as _date
from datetime import timedelta

from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone

from rhcontrol.models import Employee, Vacation
from rhcontrol.services import get_upcoming_events


@login_required
def dashboard_view(request):

    today = timezone.localdate()
    vacations_count = Vacation.objects.filter(end_date__gte=today).count()

    # Faixas de tempo de casa do gráfico: (admitido antes de, admitido a partir de).
    years_ago = {y: today - timedelta(days=365 * y) for y in (1, 3, 5, 10, 15)}
    tenure_ranges = [
        (None, years_ago[1]),
        (years_ago[1], years_ago[3]),
        (years_ago[3], years_ago[5]),
        (years_ago[5], years_ago[10]),
        (years_ago[10], years_ago[15]),
        (years_ago[15], None),
    ]

    def _tenure_filter(before, since):
        q = Q()
        if before:
            q &= Q(hire_date__lt=before)
        if since:
            q &= Q(hire_date__gte=since)
        return q

    # Uma consulta só para o card e as 6 barras (antes eram 8 consultas COUNT separadas).
    # O gráfico diz "por funcionário ativo", então demitidos ficam de fora.
    stats = Employee.objects.filter(termination_date__isnull=True).aggregate(
        active=Count('id'),
        **{f'range_{i}': Count('id', filter=_tenure_filter(before, since))
           for i, (before, since) in enumerate(tenure_ranges)},
    )

    events = get_upcoming_events(
        start_date=today,
        end_date=today + timedelta(days=30),
        limit=200,
    )
    _VISIBLE_LIMIT = 8

    context = {
        'active_employees_count':     stats['active'],
        'vacations_count':            vacations_count,
        'upcoming_events_count':      len(events),
        'upcoming_events_top':        events[:_VISIBLE_LIMIT],
        'upcoming_events_more_count': max(0, len(events) - _VISIBLE_LIMIT),

        'chart_data': [stats[f'range_{i}'] for i in range(len(tenure_ranges))],
    }

    return render(request, 'dashboard/pages/dashboard.html', context)

@login_required
@permission_required('rhcontrol.view_employee', raise_exception=True)
def upcoming_events_view(request):
    """
    Filtered list of upcoming HR events.

    Query params (all optional):
        start           YYYY-MM-DD  (defaults to today)
        end             YYYY-MM-DD  (defaults to start + 30d; clamped to +60d max)
        categories      comma-separated category names
        only_email      "true" / "1"
        employee_id     int
        department_id   int
    """

    today = timezone.localdate()

    # ── Parse start / end ────────────────────────────────────────
    def _parse_date(raw: str | None, fallback: _date) -> _date:
        if not raw:
            return fallback
        try:
            return _date.fromisoformat(raw)
        except ValueError:
            return fallback

    raw_start = request.GET.get('start', '')
    raw_end   = request.GET.get('end', '')

    start_date = _parse_date(raw_start, today)
    end_date   = _parse_date(raw_end, start_date + timedelta(days=30))

    # Clamp so users can't request > 60 days (service hard-caps at 180)
    MAX_USER_DAYS = 60
    if (end_date - start_date).days > MAX_USER_DAYS:
        end_date = start_date + timedelta(days=MAX_USER_DAYS)
    if end_date < start_date:
        end_date = start_date + timedelta(days=30)

    # ── Parse optional filters ────────────────────────────────────
    raw_categories = request.GET.get('categories', '').strip()
    categories = [c.strip() for c in raw_categories.split(',') if c.strip()] or None

    only_email = request.GET.get('only_email', '').lower() in ('true', '1', 'on')

    def _parse_int(raw: str | None) -> int | None:
        try:
            return int(raw) if raw else None
        except ValueError:
            return None

    employee_id   = _parse_int(request.GET.get('employee_id'))
    department_id = _parse_int(request.GET.get('department_id'))

    # ── Fetch events (single call, hard limit 200) ─────────────────
    events = get_upcoming_events(
        start_date=start_date,
        end_date=end_date,
        categories=categories,
        only_email_events=only_email,
        employee_id=employee_id,
        department_id=department_id,
        limit=200,
    )

    has_filters = any([raw_start, raw_end, raw_categories, only_email, employee_id, department_id])

    # Category choices for the filter UI (keep in sync with _UE_CATEGORY_META)
    CATEGORY_CHOICES = [
        ('BIRTHDAY',                    'Aniversário'),
        ('COMPANY_ANNIVERSARY',         'Aniversário de Empresa'),
        ('VACATION_START',              'Início de Férias'),
        ('VACATION_RETURN',             'Retorno de Férias'),
        ('TRAINING_DATE',               'Treinamento'),
        ('CAREER_PLAN_PROMOTION_DATE',  'Promoção'),
        ('CAREER_PLAN_REMINDER_WINDOW', 'Aviso de Promoção (30d)'),
        ('TRIAL_60_WARNING',            'Contrato (60 dias)'),
        ('TRIAL_90_WARNING',            'Contrato (90 dias)'),
    ]

    context = {
        'events':           events,
        'event_count':      len(events),
        'start_date':       start_date,
        'end_date':         end_date,
        'raw_start':        start_date.isoformat(),
        'raw_end':          end_date.isoformat(),
        'raw_categories':   raw_categories,
        'selected_cats':    set(categories) if categories else set(),
        'only_email':       only_email,
        'employee_id':      employee_id or '',
        'department_id':    department_id or '',
        'has_filters':      has_filters,
        'category_choices': CATEGORY_CHOICES,
    }
    return render(request, 'dashboard/pages/events/upcoming_events.html', context)