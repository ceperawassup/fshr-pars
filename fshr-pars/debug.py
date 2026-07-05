import requests
from bs4 import BeautifulSoup

url = 'https://ratings.ruchess.ru/people/619636'
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers)
resp.encoding = 'utf-8'
soup = BeautifulSoup(resp.text, 'html.parser')

# Смотрим заголовок страницы
print("TITLE:", soup.title.string if soup.title else "нет тега title")

# Ищем все таблицы
tables = soup.find_all('table')
print(f"\nНайдено таблиц: {len(tables)}")
for i, table in enumerate(tables):
    print(f"\nТаблица {i}:")
    # Классы и id таблицы
    print(f"  class: {table.get('class')}")
    print(f"  id: {table.get('id')}")
    # Заголовки столбцов
    headers = [th.get_text(strip=True) for th in table.find_all('th')]
    print(f"  заголовки: {headers}")
    # Первые 2 строки данных
    rows = table.find_all('tr')[1:3]  # первая строка — возможно заголовок, дальше данные
    for row in rows:
        cols = [td.get_text(strip=True) for td in row.find_all('td')]
        print(f"  строка: {cols}")

# Если таблиц нет, покажем весь текст (или только часть), чтобы понять структуру
if len(tables) == 0:
    print("\nТаблиц не найдено. Вот первые 2000 символов страницы:")
    print(soup.get_text()[:2000])
