# Generated by Django 5.1.4 on 2025-01-06 12:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_alter_customuser_avatar'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='avatar',
            field=models.ImageField(blank=True, default='Нет аватара', upload_to='user_images/', verbose_name='Аватар'),
        ),
    ]