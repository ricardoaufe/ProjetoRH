from django.contrib import admin
from .models import Employee, Department, JobTitle

class EmployeeAdmin(admin.ModelAdmin):
    ...

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    ...
@admin.register(JobTitle)
class JobTitleAdmin(admin.ModelAdmin):
    ...

admin.site.register(Employee, EmployeeAdmin)
