
from django import forms

from rhcontrol.forms.fields import EmployeeChoiceField, employee_choices
from rhcontrol.models.vacation import Vacation
from rhcontrol.services import validate_vacation


class VacationForm(forms.ModelForm):
    employee = EmployeeChoiceField()

    class Meta:
        model = Vacation
        fields = ["employee", "start_date", "vacation_duration", "cash_bonus"]

        widgets = {
            "start_date": forms.DateInput(
                format="%Y-%m-%d", attrs={"class": "form-control", "type": "date"}
            ),
            "vacation_duration": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "Ex: 30"}
            ),
            "cash_bonus": forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["employee"].queryset = employee_choices(keep=[self.instance.employee_id])
        # Período em que as férias caem; a view usa para avisar do pagamento em dobro.
        self.period = None

    def clean_vacation_duration(self):
        # Vale para cadastro e edição. Com 0 o model não calcula as datas
        # (fim/retorno ficam vazios) e com valor negativo o fim cai antes do início.
        duration = self.cleaned_data.get("vacation_duration")
        if duration is None or duration <= 0:
            raise forms.ValidationError("A duração deve ser maior que zero.")
        return duration

    def clean(self):
        cleaned_data = super().clean()
        employee = cleaned_data.get("employee")
        start_date = cleaned_data.get("start_date")
        duration = cleaned_data.get("vacation_duration")
        if not (employee and start_date and duration):
            return cleaned_data

        vacation = Vacation(
            pk=self.instance.pk,
            employee=employee,
            start_date=start_date,
            vacation_duration=duration,
            cash_bonus=cleaned_data.get("cash_bonus", False),
        )
        errors, self.period = validate_vacation(vacation)
        for field, message in errors.items():
            self.add_error(field, message)
        return cleaned_data

    @property
    def is_late(self):
        """Férias depois do prazo de concessão: pagas em dobro (CLT art. 137)."""
        return bool(self.period) and self.cleaned_data["start_date"] > self.period["deadline"]
