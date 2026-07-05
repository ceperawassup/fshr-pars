import asyncio
import csv
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

PLAYER_ID = "513242"   # поменяешь на нужный ID

async def get_tournament_links(page):
    # Кликаем "Все турниры" и собираем ссылки
    show_all_btn = await page.query_selector('text=Все турниры')
    if show_all_btn:
        await show_all_btn.click()
        await page.wait_for_timeout(3000)

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

async def fetch_tournament_rank(page, tournament_url):
    await page.goto(tournament_url, wait_until='networkidle')
    await page.wait_for_timeout(2000)

    html = await page.content()
    soup = BeautifulSoup(html, 'html.parser')

    # Название турнира из title
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
    player_url = f'https://ratings.ruchess.ru/people/{PLAYER_ID}'
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(player_url, wait_until='networkidle')
        await page.wait_for_timeout(3000)

        tournament_links = await get_tournament_links(page)
        print(f"Найдено турниров: {len(tournament_links)}")

        results = []
        for i, link in enumerate(tournament_links, 1):
            print(f"Обрабатываю {i}/{len(tournament_links)}: {link}")
            t_name, rank = await fetch_tournament_rank(page, link)
            if t_name is not None:  # если вернулось название, значит игрок найден
                print(f"  {t_name} → {rank if rank else 'пусто'}")
                results.append({'tournament': t_name, 'rank': rank, 'url': link})
            else:
                print(f"  Пропущен: {rank}")   # rank здесь содержит причину

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
