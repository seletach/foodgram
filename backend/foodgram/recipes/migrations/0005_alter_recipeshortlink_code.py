# Generated by Django 5.1.4 on 2025-01-06 11:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0004_alter_recipe_options_recipeshortlink'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recipeshortlink',
            name='code',
            field=models.CharField(default='fd804e', max_length=10, unique=True),
        ),
    ]