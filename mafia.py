import requests
from bs4 import BeautifulSoup
from collections import defaultdict


def fetch_html_content(url):
    """
    Выполняет GET-запрос к указанному URL и возвращает HTML-контент.
    """
    print(f"Загрузка данных с: {url}")
    try:
        # Устанавливаем заголовки, чтобы имитировать запрос из браузера
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()  # Вызывает исключение для плохих ответов (4xx или 5xx)
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка при выполнении HTTP-запроса: {e}")
        return None


def analyze_joint_games(html_content, target_nickname):
    """
    Парсит HTML, находит все игры, в которых участвовал target_nickname,
    и подсчитывает количество совместных игр (за одним столом) с другими игроками.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    joint_games_count = defaultdict(int)

    # Находим все секции игр (Квалификация, Полуфинал, Финал)
    # Ищем элементы с классом 'accordion-item', которые содержат данные об играх
    game_sections = soup.find_all('div', class_='accordion-item')

    for game_item in game_sections:
        # Находим все столы в текущей игре
        tables = game_item.find_all('table', class_='table-bordered')

        for table in tables:
            players_at_table = []
            # Ищем все строки с игроками в текущем столе
            for row in table.find('tbody').find_all('tr'):
                # Игрок находится во второй колонке (индекс 1)
                player_tds = row.find_all('td')
                if len(player_tds) > 1:
                    player_name = player_tds[1].text.strip()

                    # Игнорируем пустые места (там, где еще нет игрока)
                    if player_name and player_name != '---':
                        players_at_table.append(player_name)

            # Если целевой игрок находится за этим столом
            if target_nickname in players_at_table:
                # Увеличиваем счетчик для всех остальных игроков за этим столом
                for player in players_at_table:
                    if player != target_nickname:
                        joint_games_count[player] += 1

    return joint_games_count


def display_results(nickname, game_counts):
    """Сортирует и выводит результаты в требуемом формате."""

    if not game_counts:
        print(f"\n✅ Результаты для игрока **{nickname}** не найдены или у него нет совместных игр.")
        return

    # Сортировка от большего количества игр к меньшему
    sorted_counts = sorted(game_counts.items(), key=lambda item: item[1], reverse=True)

    print(f"\n📊 Результаты совместных игр (за ОДНИМ столом) для игрока **{nickname}**:")
    print("-----------------------------------------------------------------------")

    for player, count in sorted_counts:
        # Корректное склонение слова "игра"
        game_label = "совместных игр"
        if count == 1:
            game_label = "совместная игра"
        elif 2 <= count <= 4:
            game_label = "совместные игры"

        print(f"  > играет с {player}: **{count}** {game_label}")
    print("-----------------------------------------------------------------------")


# --- Основная логика ---
if __name__ == "__main__":

    # 1. Ввод данных пользователем
    # ⚠️ ВАЖНО: При работе с реальным сайтом может потребоваться авторизация,
    #          если страница результатов не общедоступна.
    USER_URL = input("Введите URL страницы результатов турнира: ")
    USER_NICKNAME = input("Введите свой никнейм для анализа: ")

    # 2. Получение HTML-контента
    html_content = fetch_html_content(USER_URL)

    if html_content:
        # 3. Анализ и вывод результатов
        results = analyze_joint_games(html_content, USER_NICKNAME)
        display_results(USER_NICKNAME, results)