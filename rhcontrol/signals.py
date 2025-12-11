from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Employee, EmployeeHistory

@receiver(pre_save, sender=Employee)
def create_employee_history(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_employee = Employee.objects.get(pk=instance.pk)
            
            changed = False
            history = EmployeeHistory(employee=instance)

            if old_employee.job_title != instance.job_title:
                history.old_job_title = str(old_employee.job_title)
                history.new_job_title = str(instance.job_title)
                changed = True
            
            if old_employee.current_salary != instance.current_salary:
                history.old_salary = old_employee.current_salary
                history.new_salary = instance.current_salary
                changed = True
            
            if changed:
                history.reason = "Alteração Cadastral"
                history.save()
                
        except Employee.DoesNotExist:
            pass