class UppercaseFieldsMixin:
    uppercase_fields = ()

    def clean(self):
        cleaned_data = super().clean()
        for name in self.uppercase_fields:
            value = cleaned_data.get(name)
            if value:
                cleaned_data[name] = value.upper()
        return cleaned_data