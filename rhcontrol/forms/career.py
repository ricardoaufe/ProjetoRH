from django import forms

from rhcontrol.models import CareerPlan, Department, JobTitle


class CareerPlanForm(forms.ModelForm):
    proposed_department = forms.ModelChoiceField(
        queryset=Department.objects.all(), label="Novo Setor", required=True
    )

    class Meta:
        model = CareerPlan
        fields = [
            "employee",
            "proposed_department",
            "proposed_job",
            "proposed_salary",
            "promotion_date",
        ]

        widgets = {
            "promotion_date": forms.DateInput(attrs={"type": "date"}),
            "proposed_salary": forms.TextInput(
                attrs={"placeholder": "0,00", "class": "money-input"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            if "class" in field.widget.attrs:
                field.widget.attrs["class"] += " form-control"
            else:
                field.widget.attrs["class"] = "form-control"

        if self.instance and self.instance.pk:
            self.fields["employee"].disabled = True

        self.fields["proposed_job"].queryset = JobTitle.objects.none()

        if "proposed_department" in self.data:
            try:
                department_id = int(self.data.get("proposed_department"))
                self.fields["proposed_job"].queryset = JobTitle.objects.filter(
                    department_id=department_id
                ).order_by("name")
            except (ValueError, TypeError):
                pass

        elif self.instance.pk and self.instance.proposed_job:
            self.fields[
                "proposed_department"
            ].initial = self.instance.proposed_job.department
            self.fields["proposed_job"].queryset = JobTitle.objects.filter(
                department=self.instance.proposed_job.department
            ).order_by("name")