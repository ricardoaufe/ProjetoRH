from django.contrib import admin
from .models import Employee, Department, JobTitle, Vacation, Training, NotificationLog, NotificationRecipient, NotificationRule, CareerPlan

class EmployeeAdmin(admin.ModelAdmin):
    ...

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    ...
@admin.register(JobTitle)
class JobTitleAdmin(admin.ModelAdmin):
    ...
    
admin.site.register(Employee, EmployeeAdmin)

@admin.register(Vacation)
class VacationAdmin(admin.ModelAdmin):
    ...

@admin.register(Training)
class TrainingAdmin(admin.ModelAdmin):
    ...

@admin.register(NotificationRule)
class NotificationRuleAdmin(admin.ModelAdmin):
    list_display = ("event_type", "days_in_advance", "is_active")
    list_filter = ("event_type", "is_active")


@admin.register(NotificationRecipient)
class NotificationRecipientAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "receive_all_events", "is_active")
    list_filter = ("receive_all_events", "is_active")
    search_fields = ("name", "email")


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ("rule", "employee", "reference_year", "sent_at")
    list_filter = ("rule", "reference_year")
    readonly_fields = ("sent_at",)

@admin.register(CareerPlan)
class CareerPlanAdmin(admin.ModelAdmin):
    list_display = ("employee", "created_at", "updated_at")
    readonly_fields = ("created_at", "updated_at")