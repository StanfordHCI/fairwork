# Generated by Django 2.0.4 on 2018-05-03 18:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('timerjerk', '0002_assignmentaudit'),
    ]

    operations = [
        migrations.AddField(
            model_name='hittype',
            name='payment',
            field=models.DecimalField(decimal_places=2, default=0.5, max_digits=6),
            preserve_default=False,
        ),
    ]
