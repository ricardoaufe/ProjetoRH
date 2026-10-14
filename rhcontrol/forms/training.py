from django import forms

from rhcontrol.forms.fields import EmployeeMultipleChoiceField, employee_choices
from rhcontrol.models import Training


class TrainingForm(forms.ModelForm):
    all_departments = forms.BooleanField(
        required=False,
        label="Todos os Setores",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    scheduled_employees = EmployeeMultipleChoiceField(label="Funcionários Previstos")
    attended_employees = EmployeeMultipleChoiceField(
        label="Funcionários Que Compareceram",
        widget=forms.SelectMultiple(attrs={
            "class": "form-control js-employee-select",
            "data-placeholder": "Selecione quem realmente compareceu...",
        }),
    )

    class Meta:
        model = Training
        fields = "__all__"

        widgets = {
            "start_date": forms.DateInput(
                format="%Y-%m-%d", attrs={"class": "form-control", "type": "date"}
            ),
            "end_date": forms.DateInput(
                format="%Y-%m-%d", attrs={"class": "form-control", "type": "date"}
            ),
            "training_total_hours": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "Ex: 8"}
            ),
            "is_fundamental": forms.CheckboxInput(
                attrs={"class": "form-check-input", "id": "id_is_fundamental"}
            ),
            "target_department": forms.Select(
                attrs={"class": "form-control", "id": "id_target_department"}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date and end_date < start_date:
            self.add_error(
                "end_date", "A data de término não pode ser anterior à data de início."
            )

        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Quem já está no treinamento continua na lista mesmo se desligado,
        # senão salvar a edição o removeria sem aviso.
        for name in ("scheduled_employees", "attended_employees"):
            current = self.instance.pk and getattr(self.instance, name).values_list("pk", flat=True)
            self.fields[name].queryset = employee_choices(keep=current or [])