from datetime import timedelta

import holidays
from django.db import models


class Vacation(models.Model):
    employee = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name='vacations')
    start_date = models.DateField(verbose_name="Data de Início")
    end_date = models.DateField(blank=True, null=True, verbose_name="Data de Fim")
    return_date = models.DateField(blank=True, null=True, verbose_name="Data de Retorno")
    vacation_duration= models.IntegerField(help_text='Duração em dias', verbose_name="Duração")

    #Função para verificação de feriados/dias não úteis + cálculo de data de término
    def save(self, *args, **kwargs):
        if self.start_date and self.vacation_duration:

            self.end_date = self.start_date + timedelta(days=self.vacation_duration - 1) # Calcula a data de término com base na duração
            next_day = self.end_date + timedelta(days=1) # A data retorno é o dia após o término das férias
            br_holidays = holidays.Brazil()

            #weekends and holidays check for return date
            while next_day.weekday() >= 5 or next_day in br_holidays:
                next_day += timedelta(days=1)
            self.return_date = next_day

        super().save(*args, **kwargs)

    def __str__(self):
        return f'Férias do(a) {self.employee.name} até {self.start_date} para {self.end_date}'