# Generated by Django 4.2.3 on 2023-07-07 09:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Top',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=70)),
            ],
        ),
        migrations.CreateModel(
            name='Middle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=70)),
                ('reports_to', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='DjangoAnnotation.top')),
            ],
        ),
        migrations.CreateModel(
            name='Lower',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=70)),
                ('reports_to', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='DjangoAnnotation.middle')),
            ],
        ),
    ]
