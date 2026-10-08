from django import forms

from rhcontrol.models import Employee, Training


class TrainingForm(forms.ModelForm):
    all_departments = forms.BooleanField(
        required=False,
        label="Todos os Setores",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
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
            "scheduled_employees": forms.SelectMultiple(
                attrs={
                    "class": "form-control",
                    "size": "10",
                    "id": "id_scheduled_employees",
                }
            ),
            "attended_employees": forms.SelectMultiple(
                attrs={"class": "form-control", "size": "10"}
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

        active_employees = Employee.objects.filter(
            termination_date__isnull=True
        ).order_by("name")
        if "scheduled_employees" in self.fields:
            self.fields["scheduled_employees"].queryset = active_employees
        if "attended_employees" in self.fields:
            self.fields["attended_employees"].queryset = active_employees