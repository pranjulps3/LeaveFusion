# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-09-12 00:05
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('leave_application', '0006_auto_20170912_0004'),
    ]

    operations = [
        migrations.AlterField(
            model_name='leavemigration',
            name='replacee',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='to_be_migrated', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='leavemigration',
            name='replacer',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='to_be_migrated_rep', to=settings.AUTH_USER_MODEL),
        ),
    ]
