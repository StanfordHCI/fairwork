# Generated by Django 2.0.4 on 2018-05-04 00:35

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('auditor', '0003_hittype_payment'),
    ]

    operations = [
        migrations.AlterField(
            model_name='assignmentaudit',
            name='assignment',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='auditor.Assignment'),
        ),
        migrations.AlterField(
            model_name='assignmentduration',
            name='assignment',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='auditor.Assignment'),
        ),
    ]