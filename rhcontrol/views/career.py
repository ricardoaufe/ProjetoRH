from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from rhcontrol.forms import CareerPlanForm
from rhcontrol.models import CareerPlan


@permission_required('rhcontrol.view_careerplan', raise_exception=True)
@login_required
def career_plan_list(request):
    """ View para listar todos os planos com filtros de busca, data, status e ordenação """

    plans = CareerPlan.objects.select_related('employee', 'proposed_job', 'employee__department')

    # ── Filters ──────────────────────────────────────────
    search_query = request.GET.get('search', '').strip()
    date_from    = request.GET.get('date_from', '')
    date_to      = request.GET.get('date_to', '')
    status_filter = request.GET.get('status', '')
    sort_by      = request.GET.get('sort', '-created_at')

    if search_query:
        plans = plans.filter(employee__name__icontains=search_query)

    if date_from:
        plans = plans.filter(promotion_date__gte=date_from)

    if date_to:
        plans = plans.filter(promotion_date__lte=date_to)

    if status_filter:
        plans = plans.filter(status=status_filter)

    # ── Sorting ───────────────────────────────────────────
    valid_sorts = {
        'employee__name':  'employee__name',
        '-employee__name': '-employee__name',
        'promotion_date':  'promotion_date',
        '-promotion_date': '-promotion_date',
        'created_at':      'created_at',
        '-created_at':     '-created_at',
    }
    plans = plans.order_by(valid_sorts.get(sort_by, '-created_at'))

    context = {
        'plans': plans,
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
        'status_filter': status_filter,
        'current_sort': sort_by,
        'has_filters': any([search_query, date_from, date_to, status_filter]),
    }
    return render(request, 'dashboard/pages/career/list.html', context)


@login_required
@permission_required('rhcontrol.add_careerplan', raise_exception=True)
def career_plan_create(request):
    """ View para criar um novo Plano de Carreira """
    if request.method == 'POST':
        form = CareerPlanForm(request.POST)
        if form.is_valid():

            plan = form.save(commit=False)

            plan.created_by = request.user

            plan.save()
            
            messages.success(request, f"Plano para {plan.employee.name} agendado com sucesso!")
            return redirect('rhcontrol:career_plan_list')
        else:
            messages.error(request, "Erro ao agendar o plano. Verifique os campos destacados abaixo.")
    else:
        form = CareerPlanForm()

    context = {
        'form': form,
        'is_update': False 
    }
    return render(request, 'dashboard/pages/career/form.html', context)


@login_required
@permission_required('rhcontrol.change_careerplan', raise_exception=True)
def career_plan_update(request, pk):
    """ View para editar um Plano de Carreira existente """
    plan = get_object_or_404(CareerPlan, pk=pk)

    if plan.status in [CareerPlan.PlanStatus.CONFIRMED, CareerPlan.PlanStatus.EFFECTIVE, CareerPlan.PlanStatus.CANCELLED]:
        messages.warning(request, "Acesso negado: Este plano já está bloqueado para edição.")
        return redirect('rhcontrol:career_plan_list')

    if request.method == 'POST':

        form = CareerPlanForm(request.POST, instance=plan)
        if form.is_valid():
            form.save()
            messages.success(request, f"Plano de {plan.employee.name} atualizado.")
            return redirect('rhcontrol:career_plan_list')
        else:
            messages.error(request, "Erro ao atualizar. Verifique os campos abaixo.")
    else:

        form = CareerPlanForm(instance=plan)

    context = {
        'form': form,
        'plan': plan,
        'is_update': True
    }
    return render(request, 'dashboard/pages/career/form.html', context)

@login_required
@permission_required('rhcontrol.change_careerplan', raise_exception=True)
@require_POST 
def confirm_career_plan_action(request, pk):
    """ Ação de botão: O RH aperta para dizer 'Aprovado, pode efetivar no dia D' """
    plan = get_object_or_404(CareerPlan, pk=pk)

    if plan.status == CareerPlan.PlanStatus.AWAITING_CONFIRMATION:
        plan.status = CareerPlan.PlanStatus.CONFIRMED
        plan.confirmed_at = timezone.now()
        plan.confirmed_by = request.user

        plan.save(update_fields=['status', 'confirmed_at', 'confirmed_by', 'updated_at'])
        
        messages.success(request, f"Promoção de {plan.employee.name} confirmada! O sistema efetivará o cargo no dia {plan.promotion_date.strftime('%d/%m/%Y')}.")
    else:
        messages.error(request, "Ação inválida: Este plano não está aguardando confirmação.")
        
    return redirect('rhcontrol:career_plan_list')


@login_required
@permission_required('rhcontrol.change_careerplan', raise_exception=True)
@require_POST
def cancel_career_plan(request, pk):
    """ Ação de botão: Cancela um plano de carreira. Permitido apenas para planos AGENDADOS ou AGUARDANDO CONFIRMAÇÃO. """
    plan = get_object_or_404(CareerPlan, pk=pk)

    cancellable_statuses = [
        CareerPlan.PlanStatus.SCHEDULED,
        CareerPlan.PlanStatus.AWAITING_CONFIRMATION,
        CareerPlan.PlanStatus.CONFIRMED,
    ]

    if plan.status not in cancellable_statuses:
        if plan.status == CareerPlan.PlanStatus.EFFECTIVE:
            messages.error(
                request,
                f"Não é possível cancelar o plano de {plan.employee.name}: "
                "a promoção já foi efetivada no sistema."
            )
        else:
            messages.error(
                request,
                f"Não é possível cancelar o plano de {plan.employee.name}: "
                f"status atual é '{plan.get_status_display()}'."
            )
        return redirect('rhcontrol:career_plan_list')

    cancellation_reason = request.POST.get('cancellation_reason', '').strip()

    plan.status = CareerPlan.PlanStatus.CANCELLED
    plan.cancellation_reason = cancellation_reason or 'Cancelado manualmente pelo usuário.'
    plan.save(update_fields=['status', 'cancellation_reason', 'updated_at'])

    messages.success(
        request,
        f"Plano de carreira de {plan.employee.name} foi cancelado."
    )
    return redirect('rhcontrol:career_plan_list')


@login_required
@permission_required('rhcontrol.delete_careerplan', raise_exception=True)
@require_POST
def career_plan_delete(request, pk):
    """ Ação: Hard Delete — apaga fisicamente do banco. Permitido apenas para planos AGENDADOS, AGUARDANDO CONFIRMAÇÃO ou CANCELADOS. """
    plan = get_object_or_404(CareerPlan, pk=pk)

    deletable_statuses = [
        CareerPlan.PlanStatus.SCHEDULED,
        CareerPlan.PlanStatus.AWAITING_CONFIRMATION,
        CareerPlan.PlanStatus.CANCELLED,
    ]

    if plan.status in deletable_statuses:
        employee_name = plan.employee.name
        plan.delete()
        messages.warning(request, f"O plano de {employee_name} foi excluído permanentemente do banco de dados.")
    elif plan.status == CareerPlan.PlanStatus.CONFIRMED:
        messages.warning(request, "Planos confirmados não podem ser excluídos — cancele-o primeiro se necessário.")
    elif plan.status == CareerPlan.PlanStatus.EFFECTIVE:
        messages.warning(request, "Planos efetivados não podem ser excluídos, pois fazem parte do histórico do funcionário.")
    else:
        messages.warning(request, "Este plano não pode ser excluído.")

    return redirect('rhcontrol:career_plan_list')