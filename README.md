# Foodgram Project

## Описание проекта

Представляем платформу, упрощающую жизнь кулинаров! Здесь можно делиться рецептами, находить новые интересные блюда, добавлять их в избранное и в один клик генерировать списки необходимых продуктов, чтобы готовить с удовольствием и без лишних хлопот.

## Проект разработан с использованием следующих технологий и инструментов:

## Technologies & Tools

**Backend:**

![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white)
![Django Rest Framework](https://img.shields.io/badge/Django%20REST-ff1709?style=for-the-badge&logo=django&logoColor=white&color=ff1709&labelColor=gray)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)

**Frontend:**

![React](https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)

**Инфраструктура:**

![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Docker Compose](https://img.shields.io/badge/Docker%20Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Nginx](https://img.shields.io/badge/Nginx-009639?style=for-the-badge&logo=nginx&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-2088FF?style=for-the-badge&logo=github-actions&logoColor=white)

**Языки программирования:**

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)

## Установка и запуск проекта

1. **Клонирование репозитория:**

   ```bash
   git clone https://github.com/seletach/foodgram
   cd foodgram
   ```
2. **Создаем superuser:**
    ```bash
   python manage.py createsuperuser
    ```
3. **Запускаем оркестр контейнеров**
    ```
    docker compose -f docker-compose.production.yml up --build
   ```
4. **Приложение будет доступно по адресу:**
    ```
   https://localhost:8080
   ```
6. **Дополнительные ресурсы**
   - Документация API доступна по адресу: http://localhost:8080/api/docs/
   - API доступна по адресу: http://localhost:8080/api/
7. **Адрес Проекта**
   - https://seletach.ru/
