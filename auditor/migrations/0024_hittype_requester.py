# Generated by Django 2.0.4 on 2018-05-14 02:40

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('auditor', '0023_remove_hittype_requester'),
    ]

    operations = [
        migrations.AddField(
            model_name='hittype',
            name='requester',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='auditor.Requester'),
            preserve_default=False,
        ),
    ]