# Generated by Django 2.0.4 on 2018-05-11 23:28

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('timerjerk', '0012_requester'),
    ]

    operations = [
        migrations.AddField(
            model_name='hittype',
            name='requester',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='timerjerk.Requester'),
            preserve_default=False,
        ),
    ]
