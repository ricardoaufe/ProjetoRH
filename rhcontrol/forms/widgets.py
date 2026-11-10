from django import forms


class DateInput(forms.DateInput):
    input_type = "date"

    def __init__(self, attrs=None, format="%Y-%m-%d"):
        final_attrs = {"class": "form-control"}
        final_attrs.update(attrs or {})
        super().__init__(attrs=final_attrs, format=format)


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True
