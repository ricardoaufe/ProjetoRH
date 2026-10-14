
from django import forms

from rhcontrol.forms.fields import EmployeeChoiceField, employee_choices
from rhcontrol.models.vacation import Vacation


class VacationForm(forms.ModelForm):
    employee = EmployeeChoiceField()

    class Meta:
        model = Vacation
        fields = ["employee", "start_date", "vacation_duration"]

        widgets = {
            "start_date": forms.DateInput(
                format="%Y-%m-%d", attrs={"class": "form-control", "type": "date"}
            ),
            "vacation_duration": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "Ex: 30"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["employee"].queryset = employee_choices(keep=[self.instance.employee_id])

    def clean_vacation_duration(self):
        # Vale para cadastro e edição. Com 0 o model não calcula as datas
        # (fim/retorno ficam vazios) e com valor negativo o fim cai antes do início.
        duration = self.cleaned_data.get("vacation_duration")
        if duration is None or duration <= 0:
            raise forms.ValidationError("A duração deve ser maior que zero.")
        return duration
