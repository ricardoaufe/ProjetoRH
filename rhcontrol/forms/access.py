from django import forms
from django.contrib.auth.models import Group, User

from rhcontrol.models import NotificationRecipient, NotificationRule


class RoleGroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ["name"]
        labels = {
            "name": "Nome do Perfil de Acesso",
        }
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nome do Perfil de Acesso",
                }
            ),
        }

    def save(self, commit=True):
        group = super().save(commit=False)
        if commit:
            group.save()

        return group


class SystemUserForm(forms.ModelForm):
    role = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        label="Perfil de Acesso (Cargo)",
        empty_label="Selecione um perfil",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    password = forms.CharField(
        label="Senha Temporária",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Digite uma senha inicial"}
        ),
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "username"]
        labels = {
            "first_name": "Nome",
            "last_name": "Sobrenome",
            "username": "Nome de Usuário (Login)",
        }
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "username": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ex: joao.silva"}
            ),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.is_superuser = False
        user.is_staff = False

        if commit:
            user.save()
            role = self.cleaned_data["role"]
            user.groups.set([role])

        return user


class SystemUserUpdateForm(forms.ModelForm):
    role = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        label="Perfil de Acesso (Cargo)",
        empty_label="Selecione um perfil",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    receive_all_events = forms.BooleanField(
        label="Receber notificações de TODOS os eventos",
        required=False,
        widget=forms.CheckboxInput(attrs={"id": "id_receive_all"}),
    )

    alerts = forms.ModelMultipleChoiceField(
        queryset=NotificationRule.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        label="Notificações Específicas",
        required=False,
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "username"]
        labels = {
            "first_name": "Nome",
            "last_name": "Sobrenome",
            "username": "Nome de Usuário (Login)",
        }
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "username": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, request_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            current_group = self.instance.groups.first()
            if current_group:
                self.fields["role"].initial = current_group

            # Ninguém altera o próprio perfil de acesso (evita autopromoção).
            # Campo desabilitado: o Django ignora o valor do POST e usa o initial.
            if request_user is not None and request_user.pk == self.instance.pk:
                self.fields["role"].disabled = True
                self.fields["role"].required = False
                self.fields["role"].help_text = "Você não pode alterar o seu próprio perfil de acesso."

            email = self.instance.email
            if email:
                recipient = NotificationRecipient.objects.filter(email=email).first()
                if recipient:
                    self.fields[
                        "receive_all_events"
                    ].initial = recipient.receive_all_events
                    self.fields["alerts"].initial = recipient.subscribed_rules.all()

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        alerts = cleaned_data.get("alerts")
        receive_all = cleaned_data.get("receive_all_events")

        if (alerts or receive_all) and not email:
            self.add_error(
                "email", "Para ativar alertas, é obrigatório cadastrar um e-mail."
            )
            self.add_error(
                "receive_all_events",
                "Preencha o e-mail antes de ativar as notificações.",
            )

        return cleaned_data

    def save(self, commit=True):

        old_email = None
        if self.instance.pk:
            old_email = User.objects.get(pk=self.instance.pk).email

        user = super().save(commit=False)
        if commit:
            user.save()

            role = self.cleaned_data.get("role")
            if role:
                user.groups.set([role])
            else:
                user.groups.clear()

            email = self.cleaned_data.get("email")
            receive_all = self.cleaned_data.get("receive_all_events", False)
            alerts = self.cleaned_data.get("alerts", [])

            if email:
                recipient = NotificationRecipient.objects.filter(
                    email=old_email
                ).first()
                if not recipient:
                    recipient = NotificationRecipient.objects.filter(
                        email=email
                    ).first()

                if alerts or receive_all:
                    if not recipient:
                        recipient = NotificationRecipient(email=email)

                    full_name = f"{user.first_name} {user.last_name}".strip()
                    recipient.name = full_name if full_name else user.username
                    recipient.email = email
                    recipient.receive_all_events = receive_all
                    recipient.is_active = True
                    recipient.save()

                    if receive_all:
                        recipient.subscribed_rules.clear()
                        recipient.subscribed_rules.set(alerts)

                else:
                    if recipient:
                        recipient.receive_all_events = False
                        recipient.subscribed_rules.clear()
                        recipient.is_active = False
                        recipient.save()

        return user
