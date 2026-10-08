from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class JobTitle(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(verbose_name="Descrição", default="")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='job_titles')
    base_salary= models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.name