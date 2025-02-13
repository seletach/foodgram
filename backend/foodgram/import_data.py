import csv
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'foodgram.settings')
django.setup()

from recipes.models import Ingredient


def import_ingredients_from_csv(file_path):
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        for row in reader:
            ingredient = Ingredient(name=row[0], measurement_unit=row[1])
            ingredient.save()
            print(f'Added ingredient: {ingredient}')


if __name__ == '__main__':
    # file_path = '/home/ilya/develop/foodgram3/foodgram/data/ingredients.csv'
    file_path = '/app/data/ingredients.csv'
    import_ingredients_from_csv(file_path)
