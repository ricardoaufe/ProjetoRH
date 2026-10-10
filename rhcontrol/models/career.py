from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class CareerPlan(models.Model):
    class PlanStatus(models.TextChoices):
        SCHEDULED = "SCHEDULED", "Agendado"
        AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION", "Aguardando Confirmação"
        CONFIRMED = "CONFIRMED", "Confirmado"
        EFFECTIVE = "EFFECTIVE", "Efetivo"
        CANCELLED = "CANCELLED", "Cancelado"

    employee = models.ForeignKey(
        "Employee",
        on_delete=models.CASCADE,
        related_name="career_plans",
        verbose_name="Funcionário",
    )

    current_department = models.ForeignKey(
        "Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="Setor Atual (Criação)",
    )
    current_job = models.ForeignKey(
        "JobTitle",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="Cargo Atual (Criação)",
    )
    current_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Salário Atual (Criação)",
    )

    proposed_job = models.ForeignKey(
        "JobTitle",
        on_delete=models.RESTRICT,
        related_name="+",
        verbose_name="Próximo Cargo",
    )
    proposed_salary = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Salário Proposto"
    )
    promotion_date = models.DateField(verbose_name="Data da Promoção")

    status = models.CharField(
        max_length=40,
        choices=PlanStatus.choices,
        default=PlanStatus.SCHEDULED,
        verbose_name="Status",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_plans",
    )

    confirmed_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="confirmed_plans",
    )

    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    effective_applied_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        verbose_name = "Plano de Carreira"
        verbose_name_plural = "Planos de Carreira"
        constraints = [
            models.UniqueConstraint(
                fields=["employee"],
                condition=models.Q(
                    status__in=["SCHEDULED", "AWAITING_CONFIRMATION", "CONFIRMED"]
                ),
                name="unique_active_career_plan",
            )
        ]

    def clean(self):
        super().clean()

        if self.pk:
            old_instance = CareerPlan.objects.get(pk=self.pk)

            if old_instance.status in [
                self.PlanStatus.CONFIRMED,
                self.PlanStatus.EFFECTIVE,
                self.PlanStatus.CANCELLED,
            ] and (
                old_instance.proposed_job != self.proposed_job
                or old_instance.proposed_salary != self.proposed_salary
                or old_instance.promotion_date != self.promotion_date
                or old_instance.employee != self.employee
            ):
                raise ValidationError(
                    "Não é possível alterar funcionário, cargo, salário ou data de um plano que já foi Confirmado, Efetivado ou Cancelado."
                )

        if (
            not self.pk
            and self.promotion_date
            and self.promotion_date <= timezone.localdate()
        ):
            raise ValidationError(
                {
                    "promotion_date": "A data da promoção deve ser estritamente no futuro."
                }
            )

        if not self.pk and self.employee:
            has_active_plan = CareerPlan.objects.filter(
                employee=self.employee,
                status__in=[
                    self.PlanStatus.SCHEDULED,
                    self.PlanStatus.AWAITING_CONFIRMATION,
                    self.PlanStatus.CONFIRMED,
                ],
            ).exists()
            if has_active_plan:
                raise ValidationError(
                    "Este funcionário já possui um plano de carreira ativo."
                )

    def save(self, *args, **kwargs):
        if not self.pk and self.employee:
            self.current_department = self.employee.department
            self.current_job = self.employee.job_title
            self.current_salary = self.employee.current_salary

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.name} -> {self.proposed_job.name} ({self.get_status_display()})"
