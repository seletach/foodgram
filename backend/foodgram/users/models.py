from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """Расширение модели пользователя."""

    first_name = models.CharField(max_length=150,
                                  verbose_name='Имя')
    last_name = models.CharField(max_length=150,
                                 verbose_name='Фамилия')
    email = models.EmailField(max_length=254,
                              unique=True,
                              verbose_name='Электронная почта')
    avatar = models.ImageField(
        verbose_name='Аватар',
        upload_to='user_images/',
        blank=True
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username


class Subscription(models.Model):
    """Подписки пользователя на других пользователей."""

    author = models.ForeignKey(
        CustomUser,
        verbose_name='Автор',
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    subscriber = models.ForeignKey(
        CustomUser,
        verbose_name='Подписчик',
        related_name='subscriber',
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'

    def __str__(self):
        return f'{self.subscriber.username} подписан на {self.author.username}'
