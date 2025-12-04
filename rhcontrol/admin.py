from django.contrib import admin
from .models import Employee, Department, JobTitle, Vacation, Training

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
