# Generated by Django 5.1.4 on 2025-01-04 14:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='avatar',
            field=models.ImageField(blank=True, upload_to='user_images/', verbose_name='Аватар'),
        ),
    ]