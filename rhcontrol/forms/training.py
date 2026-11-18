from django import forms
from django.utils import timezone

from rhcontrol.forms.fields import (
    EmployeeMultipleChoiceField,
    MultipleFileField,
    employee_choices,
)
from rhcontrol.forms.validators import validate_training_document
from rhcontrol.forms.widgets import MultipleFileInput
from rhcontrol.models import Employee, Training, TrainingDocument
from rhcontrol.models.training import (
    AUDIENCE_CHOICES,
    FORMAT_CHOICES,
    NEED_REASON_CHOICES,
    SUPPORT_DOCUMENT_CHOICES,
    VENUE_CHOICES,
    YES_NO_CHOICES,
)

# Texto que só vale quando a opção correspondente está marcada:
# campo de texto -> (campo das opções, valor que o libera).
CONDITIONAL_TEXT_FIELDS = {
    "need_other": ("need_reasons", "other"),
    "nonconformity_number": ("need_reasons", "nonconformity"),
    "venue_other": ("venues", "other"),
    "equipment_description": ("uses_equipment", "yes"),
}


def _text_input(placeholder=""):
    return forms.TextInput(attrs={"class": "form-control", "placeholder": placeholder})


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
    # Cabeçalho do Form40B: opções múltiplas guardadas como lista de códigos.
    need_reasons = forms.MultipleChoiceField(
        choices=NEED_REASON_CHOICES, required=False, label="Levantamento da Necessidade",
        widget=forms.CheckboxSelectMultiple,
    )
    venues = forms.MultipleChoiceField(
        choices=VENUE_CHOICES, required=False, label="Local do Treinamento (onde)",
        widget=forms.CheckboxSelectMultiple,
    )
    formats = forms.MultipleChoiceField(
        choices=FORMAT_CHOICES, required=False, label="Tipo",
        widget=forms.CheckboxSelectMultiple,
    )
    needs_effectiveness_check = forms.ChoiceField(
        choices=YES_NO_CHOICES, required=False, label="Necessita verificação de eficácia",
        widget=forms.RadioSelect,
    )
    audience = forms.ChoiceField(
        choices=AUDIENCE_CHOICES, required=False, label="Individual ou Grupo",
        widget=forms.RadioSelect,
    )
    uses_equipment = forms.ChoiceField(
        choices=YES_NO_CHOICES, required=False, label="Utilizado Equipamentos",
        widget=forms.RadioSelect,
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
            "is_on_the_job": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_fundamental": forms.CheckboxInput(
                attrs={"class": "form-check-input", "id": "id_is_fundamental"}
            ),
            "target_department": forms.Select(
                attrs={"class": "form-control", "id": "id_target_department"}
            ),
            "requested_by": _text_input(),
            "approved_by": _text_input(),
            "request_date": forms.DateInput(
                format="%Y-%m-%d", attrs={"class": "form-control", "type": "date"}
            ),
            "need_other": _text_input("Qual?"),
            "nonconformity_number": _text_input("Ex.: 045/2026"),
            "objective": forms.Textarea(attrs={
                "class": "form-control", "rows": 2, "maxlength": 200,
                "placeholder": "Em uma ou duas linhas: o que o treinamento busca.",
            }),
            "venue_other": _text_input("Qual local?"),
            "equipment_description": _text_input("Qual equipamento?"),
            "start_time": forms.TimeInput(format="%H:%M", attrs={"class": "form-control", "type": "time"}),
            "end_time": forms.TimeInput(format="%H:%M", attrs={"class": "form-control", "type": "time"}),
            "instructor": _text_input("Se vazio, sai o \"Ministrado por\""),
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
        if cleaned_data.get("is_integration") and scheduled is not None:
            # Na integração não há confirmação de presença: vinculou, fez.
            cleaned_data["attended_employees"] = scheduled
        elif scheduled is not None and attended is not None:
            cleaned_data["attended_employees"] = attended.filter(pk__in=scheduled)

        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")
        if start_time and end_time and end_time < start_time:
            self.add_error("end_time", "O horário de fim não pode ser anterior ao de início.")

        # Texto de uma opção desmarcada não vai para o banco nem para o Excel.
        for text_field, (options_field, value) in CONDITIONAL_TEXT_FIELDS.items():
            chosen = cleaned_data.get(options_field) or []
            if value not in (chosen if isinstance(chosen, list) else [chosen]):
                cleaned_data[text_field] = ""

        self.instance.support_documents = {
            code: cleaned_data.get(f"doc_{code}_detail", "").strip()
            for code, _ in SUPPORT_DOCUMENT_CHOICES
            if cleaned_data.get(f"doc_{code}")
        }
        return cleaned_data

    def support_document_fields(self):
        """Pares (caixinha, campo "qual, data e revisão") para o template."""
        return [(self[f"doc_{code}"], self[f"doc_{code}_detail"]) for code, _ in SUPPORT_DOCUMENT_CHOICES]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Documentos de Apoio: uma caixinha e um texto por tipo, guardados juntos
        # no campo support_documents ({código: "qual, data e revisão"}).
        self.fields.pop("support_documents")
        saved_documents = self.instance.support_documents or {}
        for code, label in SUPPORT_DOCUMENT_CHOICES:
            self.fields[f"doc_{code}"] = forms.BooleanField(
                required=False, label=label, initial=code in saved_documents,
            )
            self.fields[f"doc_{code}_detail"] = forms.CharField(
                required=False, max_length=150, label="Qual, data e revisão",
                initial=saved_documents.get(code, ""), widget=_text_input("Qual, data e revisão"),
            )

        if not self.instance.pk:
            self.initial.setdefault("request_date", timezone.localdate())
            self.initial.setdefault("formats", ["training"])

        for name in ("scheduled_employees", "attended_employees"):
            current = self.instance.pk and getattr(self.instance, name).values_list("pk", flat=True)
            self.fields[name].queryset = employee_choices(keep=current or [])

        # Ativos que não estão em nenhuma integração (ex.: admitidos antes de o
        # treinamento de integração existir), para o botão que os adiciona.
        self.employees_without_integration = list(
            Employee.objects.filter(termination_date__isnull=True)
            .exclude(scheduled_trainings__is_integration=True)
            .values_list("pk", flat=True)
        )

        # A confirmação oferece só os participantes salvos ("Destes previstos, quem veio?").
        if self.instance.pk:
            self.fields["attended_employees"].queryset = (
                self.instance.scheduled_employees.select_related("department").order_by("name")
            )
            # Só dá para remover documentos do próprio treinamento.
            self.fields["remove_documents"].queryset = self.instance.documents.all()
