# Generated by Django 5.1.4 on 2025-01-06 12:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_customuser_avatar'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='avatar',
            field=models.ImageField(blank=True, default='', upload_to='user_images/', verbose_name='Аватар'),
        ),
    ]
