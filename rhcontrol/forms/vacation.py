
from django import forms

from rhcontrol.models.vacation import Vacation


class VacationForm(forms.ModelForm):
    class Meta:
        model = Vacation
        fields = ["employee", "start_date", "vacation_duration"]

        widgets = {
            "employee": forms.Select(attrs={"class": "form-control"}),
            "start_date": forms.DateInput(
                format="%Y-%m-%d", attrs={"class": "form-control", "type": "date"}
            ),
            "vacation_duration": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "Ex: 30"}
            ),
        }