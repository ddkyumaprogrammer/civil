# Generated by Django 2.1.7 on 2019-03-20 23:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('meeting', '0006_auto_20190320_1525'),
    ]

    operations = [
        migrations.AddField(
            model_name='peoples',
            name='email_verified',
            field=models.BooleanField(default=False, verbose_name='پست الکترونیکی تأیید شده'),
        ),
        migrations.AddField(
            model_name='peoples',
            name='mobile_verified',
            field=models.BooleanField(default=False, verbose_name='موبایل تأیید شده'),
        ),
    ]
