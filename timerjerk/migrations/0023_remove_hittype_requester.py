# Generated by Django 2.0.4 on 2018-05-14 02:40

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('timerjerk', '0022_auto_20180513_1939'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='hittype',
            name='requester',
        ),
    ]