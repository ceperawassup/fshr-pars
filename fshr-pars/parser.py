import asyncio
import csv
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import re

PLAYER_ID = "600057"   # поменяй при необходимости

async def get_max_page(page):
    """Определяет максимальный номер страницы в пагинации."""
    pagination = await page.query_selector('ul.pagination')
    if not pagination:
        return 1
    # Ищем все ссылки с href, содержащим ?page=
    links = await pagination.query_selector_all('a[href*="?page="]')
    max_page = 1
    for link in links:
        href = await link.get_attribute('href')
        if href:
            match = re.search(r'page=(\d+)', href)
            if match:
                max_page = max(max_page, int(match.group(1)))
    return max_page

async def collect_tournament_links_from_page(page):
    """Собирает ссылки на турниры с текущей страницы."""
    html = await page.content()
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', class_='table')
    if not table:
        return []
    links = []
    for row in table.find_all('tr')[1:]:
        cells = row.find_all('td')
        if not cells:
            continue
        link_tag = cells[0].find('a')
        if link_tag and link_tag.get('href'):
            full_url = 'https://ratings.ruchess.ru' + link_tag['href']
            links.append(full_url)
    return links

async def get_all_tournament_links(page, player_id):
    """Переходит по всем страницам и собирает ссылки на турниры."""
    # Переходим сразу на страницу tournaments (первая страница)
    base_url = f'https://ratings.ruchess.ru/people/{player_id}/tournaments'
    await page.goto(base_url, wait_until='networkidle')
    await page.wait_for_timeout(3000)

    # Определяем максимальную страницу
    max_page = await get_max_page(page)
    print(f"Обнаружено страниц: {max_page}")

    all_links = []
    for p in range(1, max_page + 1):
        if p > 1:
            page_url = f'{base_url}?page={p}'
            await page.goto(page_url, wait_until='networkidle')
            await page.wait_for_timeout(2000)

        links = await collect_tournament_links_from_page(page)
        all_links.extend(links)
        print(f"Страница {p}: собрано {len(links)} турниров (всего {len(all_links)})")

    return all_links

async def fetch_tournament_rank(page, tournament_url):
    await page.goto(tournament_url, wait_until='networkidle')
    await page.wait_for_timeout(2000)

    html = await page.content()
    soup = BeautifulSoup(html, 'html.parser')

    title_tag = soup.find('title')
    tournament_name = title_tag.get_text(strip=True) if title_tag else tournament_url

    table = soup.find('table', class_='table-bordered')
    if not table:
        return None, "таблица не найдена"

    for row in table.find_all('tr')[1:]:
        cells = row.find_all('td')
        if not cells:
            continue
        name_cell = cells[2] if len(cells) > 2 else None
        if name_cell:
            link = name_cell.find('a', href=lambda h: h and f'/people/{PLAYER_ID}' in h)
            if link:
                rank = cells[-1].get_text(strip=True) if cells[-1] else ''
                return tournament_name, rank

    return None, "игрок не найден"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        tournament_links = await get_all_tournament_links(page, PLAYER_ID)
        print(f"\nВсего найдено турниров: {len(tournament_links)}")

        results = []
        for i, link in enumerate(tournament_links, 1):
            print(f"Обрабатываю {i}/{len(tournament_links)}: {link}")
            t_name, rank = await fetch_tournament_rank(page, link)
            if t_name is not None:
                print(f"  {t_name} → {rank if rank else 'пусто'}")
                results.append({'tournament': t_name, 'rank': rank, 'url': link})
            else:
                print(f"  Пропущен: {rank}")

        await browser.close()

    if results:
        print("\n=== РЕЗУЛЬТАТЫ ===")
        for r in results:
            print(f"{r['tournament']} | {r['rank']}")

        with open('ranks.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['tournament', 'rank', 'url'])
            writer.writeheader()
            writer.writerows(results)
        print("Результаты сохранены в ranks.csv")
    else:
        print("Нет данных о разрядах.")

if __name__ == '__main__':
    asyncio.run(main())
