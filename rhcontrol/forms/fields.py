from decimal import Decimal, InvalidOperation

from django import forms


class BRLDecimalField(forms.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", forms.TextInput(
            attrs={"class": "form-control money-input", "placeholder": "0,00"}
        ))
        super().__init__(*args, **kwargs)

    def prepare_value(self, value):
        if isinstance(value, Decimal):
            return f"{value:.2f}".replace(".", ",")
        return value

    def clean(self, value):
        value = super().clean(value)
        if value in (None, ""):
            return None
        try:
            return Decimal(str(value).replace(".", "").replace(",", "."))
        except InvalidOperation:
            raise forms.ValidationError("Valor inválido")