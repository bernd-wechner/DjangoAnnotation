# Generated by Django 4.2.3 on 2023-07-07 10:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('DjangoAnnotation', '0002_alter_lower_reports_to_alter_middle_reports_to'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lower',
            name='reports_to',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lowers', to='DjangoAnnotation.middle'),
        ),
    ]
