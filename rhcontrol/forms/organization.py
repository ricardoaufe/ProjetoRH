from decimal import Decimal

from django import forms

from rhcontrol.models.organization import Department, JobTitle


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ["name", "description"]
        labels = {
            "name": "Nome do Setor",
            "description": "Descrição do Setor",
        }
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Nome do Setor"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Descrição do Setor",
                    "rows": 3,
                }
            ),
        }


class JobTitleForm(forms.ModelForm):
    base_salary = forms.CharField(
        label="Salário Base",
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control money-input", "placeholder": "0,00"}
        ),
    )

    class Meta:
        model = JobTitle
        fields = ["name", "base_salary", "description"]
        labels = {
            "name": "Nome do Cargo",
            "base_salary": "Salário Base",
            "description": "Descrição",
        }
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Nome do Cargo"}
            ),
            "base_salary": forms.TextInput(
                attrs={"class": "form-control money-input", "placeholder": "0,00"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Descrição (Opcional)",
                    "rows": 1,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.base_salary:
            self.initial["base_salary"] = f"{self.instance.base_salary:.2f}".replace(
                ".", ","
            )

    def clean_base_salary(self):
        salary = self.cleaned_data.get("base_salary")
        if not salary:
            return None

        if isinstance(salary, (float, int, Decimal)):
            return salary

        salary_str = str(salary).replace(".", "").replace(",", ".")

        try:
            return Decimal(salary_str)

        except Exception:
            raise forms.ValidationError("Valor inválido")


JobTitleFormSet = forms.inlineformset_factory(
    Department, JobTitle, form=JobTitleForm, extra=0, can_delete=True
)