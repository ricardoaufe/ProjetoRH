from decimal import Decimal, InvalidOperation

from django import forms
from django.utils import timezone

from rhcontrol.models import Dependent, Employee, EmployeeHistory, JobTitle

from .validators import validate_cpf


class EmployeeForm(forms.ModelForm):
    current_salary = forms.CharField(
        label="Salário Atual",
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control money-input", "placeholder": "0,00"}
        ),
    )

    change_date = forms.DateField(
        label="Data da Alteração (Histórico)",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        help_text="Se houver mudança de cargo/setor/salário, qual a data de vigência?",
    )

    change_reason = forms.ChoiceField(
        label="Motivo da Alteração",
        required=False,
        choices=[
            ("", "--- Selecione o Motivo ---"),
            ("Promoção", "Promoção"),
            ("Mérito", "Mérito"),
            ("Dissídio", "Dissídio"),
            ("Mudança de Setor", "Mudança de Setor"),
            ("Mudança de Horário", "Mudança de Horário"),
            ("Erro de Cadastro", "Correção de Erro"),
        ],
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    special_workday_other = forms.CharField(
        label="Qual Trabalho Especial?",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Descreva o trabalho especial",
            }
        ),
    )

    class Meta:
        model = Employee
        fields = "__all__"
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control uppercase-input"}),
            "mother_name": forms.TextInput(
                attrs={"class": "form-control uppercase-input"}
            ),
            "birth_date": forms.DateInput(
                format="%Y-%m-%d", attrs={"type": "date", "class": "form-control"}
            ),
            "hire_date": forms.DateInput(
                format="%Y-%m-%d", attrs={"type": "date", "class": "form-control"}
            ),
            "rg_issue_date": forms.DateInput(
                format="%Y-%m-%d", attrs={"type": "date", "class": "form-control"}
            ),
            "ctps_issue_date": forms.DateInput(
                format="%Y-%m-%d", attrs={"type": "date", "class": "form-control"}
            ),
            "admission_exam_date": forms.DateInput(
                format="%Y-%m-%d", attrs={"type": "date", "class": "form-control"}
            ),
            "termination_date": forms.DateInput(
                format="%Y-%m-%d", attrs={"type": "date", "class": "form-control"}
            ),
            "arrival_date": forms.DateInput(
                format="%Y-%m-%d", attrs={"type": "date", "class": "form-control"}
            ),
            "naturalization_date": forms.DateInput(
                format="%Y-%m-%d", attrs={"type": "date", "class": "form-control"}
            ),
            "rne_issue_date": forms.DateInput(
                format="%Y-%m-%d", attrs={"type": "date", "class": "form-control"}
            ),
            "cipa_mandate_start_date": forms.DateInput(
                format="%Y-%m-%d", attrs={"type": "date", "class": "form-control"}
            ),
            "cipa_mandate_end_date": forms.DateInput(
                format="%Y-%m-%d", attrs={"type": "date", "class": "form-control"}
            ),
            "department": forms.Select(attrs={"class": "form-control"}),
            "job_title": forms.Select(attrs={"class": "form-control"}),
            "cpf": forms.TextInput(
                attrs={
                    "class": "form-control cpf-input",
                    "placeholder": "000.000.000-00",
                }
            ),
            "mobile_phone": forms.TextInput(
                attrs={
                    "class": "form-control phone-input",
                    "placeholder": "(00) 00000-0000",
                }
            ),
            "emergency_phone": forms.TextInput(
                attrs={
                    "class": "form-control phone-input",
                    "placeholder": "(00) 00000-0000",
                }
            ),
            "zip_code": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "00000-000"}
            ),
            "contract_end_date": forms.DateInput(
                format="%Y-%m-%d", attrs={"type": "date", "class": "form-control"}
            ),
        }

    def clean_cpf(self):
        cpf = self.cleaned_data.get("cpf")
        if not validate_cpf(cpf):
            raise forms.ValidationError("CPF Inválido ou Inexistente.")
        return cpf

    def clean_birth_date(self):
        birth_date = self.cleaned_data.get("birth_date")

        if birth_date:
            today = timezone.localdate()
            age = (
                today.year
                - birth_date.year
                - ((today.month, today.day) < (birth_date.month, birth_date.day))
            )
            if age < 14:
                raise forms.ValidationError(
                    "O funcionário deve ter pelo menos 14 anos."
                )

            if age > 100:
                raise forms.ValidationError(
                    "Idade inválida. Verifique o ano de nascimento (Máx: 100 anos)."
                )
        return birth_date

    def clean_name(self):
        name = self.cleaned_data.get("name")
        if name:
            return name.upper()
        return name

    def clean_mother_name(self):
        mother_name = self.cleaned_data.get("mother_name")
        if mother_name:
            return mother_name.upper()
        return mother_name

    def clean_current_salary(self):
        salary = self.cleaned_data.get("current_salary")
        if not salary:
            return None
        salary_str = str(salary).replace(".", "").replace(",", ".")
        try:
            return Decimal(salary_str)
        except InvalidOperation:
            raise forms.ValidationError("Valor inválido") from None

    def clean_old_salary(self):
        salary = self.cleaned_data.get("old_salary")
        if not salary:
            return None
        salary_str = str(salary).replace(".", "").replace(",", ".")
        try:
            return Decimal(salary_str)
        except InvalidOperation:
            raise forms.ValidationError("Valor inválido") from None

    def clean(self):
        cleaned_data = super().clean()

        hire_date = cleaned_data.get("hire_date")
        termination_date = cleaned_data.get("termination_date")

        if hire_date and termination_date:
            if termination_date < hire_date:
                self.add_error(
                    "termination_date",
                    "A data de demissão não pode ser anterior à data de admissão.",
                )

        special_workday = cleaned_data.get("special_workday")
        special_workday_other = cleaned_data.get("special_workday_other")

        if special_workday == "Outro" and not special_workday_other:
            self.add_error(
                "special_workday_other",
                "Por favor, especifique qual é o trabalho especial.",
            )

        if special_workday != "Outro":
            cleaned_data["special_workday_other"] = ""

        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk and self.instance.current_salary:
            self.initial["current_salary"] = (
                f"{self.instance.current_salary:.2f}".replace(".", ",")
            )

        if "department" in self.data:
            try:
                department_id = int(self.data.get("department"))
                self.fields["job_title"].queryset = JobTitle.objects.filter(
                    department_id=department_id
                ).order_by("name")
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.department:
            self.fields[
                "job_title"
            ].queryset = self.instance.department.job_titles.order_by("name")
        else:
            self.fields["job_title"].queryset = JobTitle.objects.none()

        for field in self.fields.values():
            if isinstance(field.widget, forms.DateInput):
                field.widget.attrs.update({"class": "form-control", "type": "date"})


class EmployeeHistoryForm(forms.ModelForm):
    class Meta:
        model = EmployeeHistory
        fields = [
            "date_changed",
            "reason",
            "old_job_title",
            "new_job_title",
            "old_salary",
            "new_salary",
            "old_cipa_role",
            "new_cipa_role",
            "old_department",
            "new_department",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        dynamic_fields = [
            "old_job_title",
            "new_job_title",
            "old_salary",
            "new_salary",
            "old_cipa_role",
            "new_cipa_role",
            "old_department",
            "new_department",
        ]

        for field_name in dynamic_fields:
            if field_name in self.fields:
                self.fields[field_name].required = False

class DependentForm(forms.ModelForm):
    class Meta:
        model = Dependent
        fields = ["name", "cpf", "birth_date", "relationship_type", "has_disability"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control uppercase-input",
                    "placeholder": "Nome Completo",
                }
            ),
            "cpf": forms.TextInput(
                attrs={
                    "class": "form-control cpf-input cpf-input",
                    "placeholder": "000.000.000-00",
                }
            ),
            "birth_date": forms.DateInput(
                format="%Y-%m-%d", attrs={"type": "date", "class": "form-control"}
            ),
            "relationship_type": forms.Select(
                attrs={"class": "form-control form-select"}
            ),
        }

    def clean_name(self):
        name = self.cleaned_data.get("name")
        if name:
            return name.upper()
        return name

    def clean_cpf(self):
        cpf = self.cleaned_data.get("cpf")
        if not validate_cpf(cpf):
            raise forms.ValidationError("CPF Inválido ou Inexistente.")
        return cpf


DependentFormSet = forms.inlineformset_factory(
    Employee, Dependent, form=DependentForm, extra=0, can_delete=True
)

