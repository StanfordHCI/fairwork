# Generated by Django 2.0.5 on 2019-05-16 19:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auditor', '0017_auto_20190311_1456'),
    ]

    operations = [
        migrations.AddField(
            model_name='assignmentduration',
            name='measured_time',
            field=models.DurationField(blank=True, null=True),
        ),
    ]
