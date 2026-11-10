from django import forms

from rhcontrol.forms.fields import (
    EmployeeMultipleChoiceField,
    MultipleFileField,
    employee_choices,
)
from rhcontrol.forms.validators import validate_training_document
from rhcontrol.forms.widgets import MultipleFileInput
from rhcontrol.models import Training, TrainingDocument


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
    documents = MultipleFileField(
        required=False,
        label="Documentos escaneados",
        help_text="PDF, JPG ou PNG. Escolha vários de uma vez ou um por vez: todos vão juntos ao salvar.",
        validators=[validate_training_document],
        widget=MultipleFileInput(attrs={
            "class": "form-control",
            "accept": ".pdf,.jpg,.jpeg,.png",
        }),
    )
    # Só documentos deste treinamento: o queryset é definido no __init__.
    remove_documents = forms.ModelMultipleChoiceField(
        queryset=TrainingDocument.objects.none(),
        required=False,
        label="Remover documentos",
        widget=forms.CheckboxSelectMultiple,
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

        scheduled = cleaned_data.get("scheduled_employees")
        attended = cleaned_data.get("attended_employees")
        if scheduled is not None and attended is not None:
            cleaned_data["attended_employees"] = attended.filter(pk__in=scheduled)

        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name in ("scheduled_employees", "attended_employees"):
            current = self.instance.pk and getattr(self.instance, name).values_list("pk", flat=True)
            self.fields[name].queryset = employee_choices(keep=current or [])

        # A confirmação oferece só os participantes salvos ("Destes previstos, quem veio?").
        if self.instance.pk:
            self.fields["attended_employees"].queryset = (
                self.instance.scheduled_employees.select_related("department").order_by("name")
            )
            # Só dá para remover documentos do próprio treinamento.
            self.fields["remove_documents"].queryset = self.instance.documents.all()
