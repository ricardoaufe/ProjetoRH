"""
views_occurrence.py — CRUD views for the Occurrence model.

All views are nested under an employee:
    employees/<employee_id>/occurrences/...

Access requires the matching rhcontrol.*_occurrence permission.
Anonymous users are redirected to the login page; authenticated users
without the permission receive HTTP 403. (PermissionRequiredMixin does
this by default — setting raise_exception=True would send anonymous users
a 403 too.)
"""
# ---------------------------------------------------------------------------
# Base mixin — re-uses the project mixin; imported here for clarity.
# ---------------------------------------------------------------------------
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView, DeleteView, ListView, UpdateView, View

from rhcontrol.filters import filter_occurrences
from rhcontrol.forms import OccurrenceForm
from rhcontrol.models import CID, Employee, Occurrence

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _occurrence_list_url(employee_id: int) -> str:
    return reverse('rhcontrol:occurrence_list', kwargs={'employee_id': employee_id})


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

class OccurrenceListView(PermissionRequiredMixin, ListView):
    """
    GET  employees/<employee_id>/occurrences/
    Shows all occurrences for the given employee, most recent first.
    Paginated at 20 per page.
    """

    permission_required = 'rhcontrol.view_occurrence'
    template_name = 'dashboard/pages/occurrence/list.html'
    context_object_name = 'occurrences'
    paginate_by = 20

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.employee = get_object_or_404(Employee, pk=self.kwargs['employee_id'])
        
    def get_queryset(self):
        queryset = Occurrence.objects.filter(employee=self.employee).select_related('created_by', 'updated_by')
        return filter_occurrences(queryset, self.request.GET)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['employee'] = self.employee
        ctx['search_query'] = self.request.GET.get('search', '')
        ctx['date_from'] = self.request.GET.get('date_from', '')
        ctx['date_to'] = self.request.GET.get('date_to', '')
        ctx['sort_by'] = self.request.GET.get('sort', '-occurrence_date')
        
        return ctx


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

class OccurrenceCreateView(PermissionRequiredMixin, CreateView):
    """
    GET/POST  employees/<employee_id>/occurrences/create/
    Creates a new occurrence linked to the employee.
    Sets employee, created_by, and updated_by from the request context.
    """

    permission_required = 'rhcontrol.add_occurrence'
    template_name = 'dashboard/pages/occurrence/form.html'
    form_class = OccurrenceForm

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.employee = get_object_or_404(Employee, pk=self.kwargs['employee_id'])

    def form_valid(self, form):
        occurrence = form.save(commit=False)
        occurrence.employee = self.employee
        occurrence.created_by = self.request.user
        occurrence.updated_by = self.request.user
        # Form already validated occurrence_date via clean_occurrence_date().
        # Use Model.save() directly to skip Occurrence.save()'s full_clean() call
        # and avoid raising the same error a second time as a non-field error.
        occurrence.save()
        return redirect(_occurrence_list_url(self.employee.pk))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['employee'] = self.employee
        ctx['title'] = 'Nova Ocorrência'
        ctx['form_action'] = reverse(
            'rhcontrol:occurrence_create',
            kwargs={'employee_id': self.employee.pk},
        )
        return ctx


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

class OccurrenceUpdateView(PermissionRequiredMixin, UpdateView):
    """
    GET/POST  employees/<employee_id>/occurrences/<pk>/edit/
    Edits an existing occurrence that belongs to the employee.
    Sets updated_by on every save.
    """
    permission_required = 'rhcontrol.change_occurrence'
    template_name = 'dashboard/pages/occurrence/form.html'
    form_class = OccurrenceForm

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.employee = get_object_or_404(Employee, pk=self.kwargs['employee_id'])

    def get_queryset(self):
        # Enforces the nesting constraint: occurrence must belong to employee.
        return Occurrence.objects.filter(employee=self.employee)

    def form_valid(self, form):
        occurrence = form.save(commit=False)
        occurrence.updated_by = self.request.user
        # Form already validated occurrence_date via clean_occurrence_date().
        # Use Model.save() directly to skip Occurrence.save()'s full_clean() call.
        occurrence.save()
        return redirect(_occurrence_list_url(self.employee.pk))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['employee'] = self.employee
        ctx['title'] = 'Editar Ocorrência'
        ctx['form_action'] = reverse(
            'rhcontrol:occurrence_update',
            kwargs={'employee_id': self.employee.pk, 'pk': self.object.pk},
        )
        return ctx


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

class OccurrenceDeleteView(PermissionRequiredMixin, DeleteView):
    """
    GET/POST  employees/<employee_id>/occurrences/<pk>/delete/
    Shows confirmation page (GET) and hard-deletes on POST.
    """
    permission_required = 'rhcontrol.delete_occurrence'
    template_name = 'dashboard/pages/occurrence/confirm_delete.html'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.employee = get_object_or_404(Employee, pk=self.kwargs['employee_id'])

    def get_queryset(self):
        # Enforces the nesting constraint.
        return Occurrence.objects.filter(employee=self.employee)

    def get_success_url(self):
        return _occurrence_list_url(self.employee.pk)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['employee'] = self.employee
        return ctx
    
class AjaxSearchCidsView(PermissionRequiredMixin, View):
    permission_required = 'rhcontrol.view_occurrence'

    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '').strip()

        if len(query) < 2:
            return JsonResponse({'results': []})

        cids = CID.objects.filter(
            Q(code__icontains=query) | Q(description__icontains=query)
        )[:20]
        
        results = [
            {'id': cid.id, 'text': f"{cid.code} - {cid.description}"}
            for cid in cids
        ]
        
        return JsonResponse({'results': results})