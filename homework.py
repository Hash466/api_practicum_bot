from dotenv import load_dotenv
import logging
import os
import requests
import time
from telegram import Bot


load_dotenv()

PRAKTIKUM_TOKEN = os.getenv("PRAKTIKUM_TOKEN")
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


def parse_homework_status(homework):
    """
    разобрать ответ API

    Args:
        homework (dict): данные с описанием, статусом и т.п. домашки

    Returns:
        (str): сообщение с текущим статусом домашки
    """
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    if status == 'rejected':
        return (f'У вас проверили работу "{homework_name}"!\n\n'
                'К сожалению в работе нашлись ошибки.')
    if status == 'approved':
        return (f'У вас проверили работу "{homework_name}"!\n\n'
                'Ревьюеру всё понравилось, можно приступать к следующему '
                'уроку.')
    if status == 'reviewing':
        return (f'Ваша работа "{homework_name}" в данный момент проходит '
                'ревью.\n\nМолитесь всем Богам, или предложите ревьюверу '
                'бутылочку нормального пойла, дабы задобрить уважаемого!')


def get_homework_statuses(current_timestamp):
    """
    Запросить статус домашки через API

    Args:
        current_timestamp (int): начало интервала времени

    Returns:
        (dict): в зависимости от ответа возможно:
            {'homeworks': [], 'current_date': 1622751338};
            {'homeworks': [{...},], 'current_date': 1622752114}
    """
    headers = {
        'Authorization': f'OAuth {PRAKTIKUM_TOKEN}'
    }
    params = {
        'from_date': current_timestamp
    }
    homework_statuses = requests.get(
        'https://praktikum.yandex.ru/api/user_api/homework_statuses/',
        headers=headers,
        params=params
    )
    return homework_statuses.json()


def send_message(message, bot_client):
    return bot_client.send_message(CHAT_ID, message)


def main():
    logging.basicConfig(level=logging.DEBUG)
    logging.basicConfig(
        format=(
            '%(asctime)s, %(levelname)s, %(name)s, %(filename)s, '
            '%(funcName)s, %(lineno)s, %(message)s'
        )
    )
    logging.basicConfig(filename='main.log', filemode='w')

    t_bot = Bot(token=TELEGRAM_TOKEN)
    # current_timestamp = int(time.time())  # начальное значение timestamp
    # current_timestamp = (int(time.time()) - (5 * 60))
    current_timestamp = 0

    while True:
        try:
            new_homework = get_homework_statuses(current_timestamp)
            homeworks = new_homework.get('homeworks')
            if homeworks:
                send_message(parse_homework_status(homeworks[0]), t_bot)
            current_timestamp = new_homework.get('current_date',
                                                 current_timestamp)
            time.sleep(300)

        except Exception as e:
            print(f'Бот столкнулся с ошибкой: {e}')
            time.sleep(5)


if __name__ == '__main__':
    main()
