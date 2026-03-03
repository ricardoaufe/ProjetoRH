from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('rhcontrol', '0027_rename_training_duration_training_training_total_hours_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Add the attachment FileField
        migrations.AddField(
            model_name='occurrence',
            name='attachment',
            field=models.FileField(blank=True, null=True, upload_to='occurrences/', verbose_name='Anexo'),
        ),
        # Add the updated_by FK
        migrations.AddField(
            model_name='occurrence',
            name='updated_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='occurrences_updated',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Atualizado por',
            ),
        ),
        # Fix created_by: add verbose_name + correct related_name
        migrations.AlterField(
            model_name='occurrence',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='occurrences_created',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Criado por',
            ),
        ),
        # Fix employee: add verbose_name
        migrations.AlterField(
            model_name='occurrence',
            name='employee',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='occurrences',
                to='rhcontrol.employee',
                verbose_name='Funcionário',
            ),
        ),
        # Fix occurrence_date verbose_name
        migrations.AlterField(
            model_name='occurrence',
            name='occurrence_date',
            field=models.DateField(verbose_name='Data da Ocorrência'),
        ),
        # Fix ordering to most-recent-first
        migrations.AlterModelOptions(
            name='occurrence',
            options={
                'ordering': ['-occurrence_date', '-created_at'],
                'verbose_name': 'Ocorrência',
                'verbose_name_plural': 'Ocorrências',
            },
        ),
    ]
