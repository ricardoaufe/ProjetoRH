from decimal import Decimal, InvalidOperation

from django import forms
from django.db.models import Q

from rhcontrol.models import Employee


class BRLDecimalField(forms.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", forms.TextInput(
            attrs={"class": "form-control money-input", "placeholder": "0,00"}
        ))
        super().__init__(*args, **kwargs)

    def prepare_value(self, value):
        if isinstance(value, Decimal):
            return f"{value:.2f}".replace(".", ",")
        return value

    def clean(self, value):
        value = super().clean(value)
        if value in (None, ""):
            return None
        try:
            return Decimal(str(value).replace(".", "").replace(",", "."))
        except InvalidOperation:
            raise forms.ValidationError("Valor inválido") from None


def employee_choices(keep=()):
    """
    Funcionários ativos em ordem alfabética, mais os de `keep` (ids já
    vinculados ao registro em edição), para que um desligado depois não
    invalide o formulário.
    """
    return (
        Employee.objects.select_related("department")
        .filter(Q(termination_date__isnull=True) | Q(pk__in=[pk for pk in keep if pk]))
        .order_by("name")
    )


def _employee_label(employee):
    if employee.department_id:
        return f"{employee.name} · {employee.department.name}"
    return employee.name


class EmployeeChoiceField(forms.ModelChoiceField):
    """
    Campo padrão para escolher UM funcionário. A classe js-employee-select
    ativa a busca por nome (base_static/global/js/employee-select.js).
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("queryset", employee_choices())
        kwargs.setdefault("label", "Funcionário")
        kwargs.setdefault("empty_label", "")
        kwargs.setdefault("widget", forms.Select(
            attrs={"class": "form-control js-employee-select"}
        ))
        super().__init__(**kwargs)

    def label_from_instance(self, obj):
        return _employee_label(obj)


class EmployeeMultipleChoiceField(forms.ModelMultipleChoiceField):
    """Mesma busca do EmployeeChoiceField, permitindo vários funcionários."""

    def __init__(self, **kwargs):
        kwargs.setdefault("queryset", employee_choices())
        kwargs.setdefault("required", False)
        kwargs.setdefault("widget", forms.SelectMultiple(
            attrs={"class": "form-control js-employee-select"}
        ))
        super().__init__(**kwargs)

    def label_from_instance(self, obj):
        return _employee_label(obj)
