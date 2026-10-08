from django import forms

from rhcontrol.models.occurrence import Occurrence


class OccurrenceForm(forms.ModelForm):
    class Meta:
        model = Occurrence

        fields = [
            "title",
            "cid",
            "description",
            "occurrence_date",
            "is_absence",
            "end_date",
        ]

        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Título da ocorrência",
                }
            ),
            "cid": forms.Select(
                attrs={"class": "form-control cid-select2", "style": "width: 100%;"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Descreva a ocorrência...",
                }
            ),
            "occurrence_date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"class": "form-control", "type": "date"},
            ),
            "end_date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"class": "form-control", "type": "date"},
            ),
            "is_absence": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk and not self.initial.get("occurrence_date"):
            from django.utils import timezone as django_tz

            self.initial["occurrence_date"] = django_tz.localdate()

    def clean_occurrence_date(self):
        from django.utils import timezone as django_tz

        date = self.cleaned_data.get("occurrence_date")
        if date and date > django_tz.localdate():
            raise forms.ValidationError("A data não pode ser no futuro.")
        return date

    def clean(self):
        cleaned_data = super().clean()

        is_absence = cleaned_data.get("is_absence")
        occurrence_date = cleaned_data.get("occurrence_date")
        end_date = cleaned_data.get("end_date")

        if not is_absence:
            cleaned_data["end_date"] = None
        else:
            if end_date and occurrence_date and end_date < occurrence_date:
                self.add_error(
                    "end_date", "A data de fim não pode ser anterior à data de início."
                )

        return cleaned_data