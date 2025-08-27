from rest_framework.pagination import PageNumberPagination

from foodgram.settings import PAGE_SIZE


class Pagination(PageNumberPagination):
    """Кастомная пагинация для API endpoints.

    Настройки:
    - page_size: Стандартное количество элементов на странице (из settings)
    - page_size_query_param: Параметр для изменения размера страницы
    - max_page_size: Максимальное количество элементов на странице

    Endpoints пагинации:
    - /api/endpoint/ - стандартная пагинация
    - /api/endpoint/?limit=10 - изменить размер страницы
    - /api/endpoint/?page=2 - перейти на страницу 2
    """

    page_size = PAGE_SIZE
    page_size_query_param = 'limit'
    max_page_size = PAGE_SIZE
