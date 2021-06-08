import logging
import os
import time
from logging.handlers import RotatingFileHandler

import requests
from json import JSONDecodeError
from dotenv import load_dotenv
from telegram import Bot

ERROR_DESCRIPTION = {
    'ConnectionError': 'Ошибка соединения!\n{err}',
    'TimeoutError': 'Время ожидание ответа истекло!\n{err}',
    'JSONDecodeError': 'Ошибка разбора json ответа сервера!\n{err}',
    'ResponseExcept': 'Ответ API содержит ошибку!\n{code}\n{message}',
    'evn_error': 'Ошибка загрузки данных из ".env": {err}',
    'status_error': 'Недокументированный статус работы "{homework_name}"!',
    'name_error': 'Отсутствует имя домашки!',
    'other_errors': 'При подключении к API возникла ошибка:\n{err}'
}

VERDICTS = {
    'rejected': ('У вас проверили работу "{homework_name}"!\n'
                 'К сожалению в работе нашлись ошибки.'),
    'approved': ('У вас проверили работу "{homework_name}"!\n'
                 'Ревьюеру всё понравилось, можно приступать к следующему '
                 'уроку.'),
    'reviewing': ('Ваша работа "{homework_name}" в данный момент проходит '
                  'ревью.\nМолитесь всем Богам, или предложите ревьюверу '
                  'бутылочку нормального пойла, дабы задобрить уважаемого!'),
}

LOG_MESSAGES = {
    'message_send': 'Отправлено сообщение: {message}',
    'bot_start': 'Бот запущен!',
    'bot_error': 'Бот столкнулся с ошибкой!:\n{err}',
}
LOG_FILENAME = 't_bot.log'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH_NAME = os.path.join(BASE_DIR, LOG_FILENAME)

load_dotenv()

API_URL = 'https://praktikum.yandex.ru/api/user_api/homework_statuses/'

try:
    PRAKTIKUM_TOKEN = os.environ['PRAKTIKUM_TOKEN']
    TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
    CHAT_ID = os.environ['TELEGRAM_CHAT_ID']
except KeyError as err:
    raise KeyError(ERROR_DESCRIPTION['evn_error'].format(err=err))

HEADERS = {'Authorization': f'OAuth {PRAKTIKUM_TOKEN}'}


def parse_homework_status(homework):
    """
    Разобрать ответ API.

    Args:
        homework (dict): данные с описанием, статусом и т.п. домашки:

    Returns:
        (str): сообщение с текущим статусом домашки
    """
    homework_name = homework.get('homework_name', 'no name')
    if homework_name == 'no name':
        raise ValueError(ERROR_DESCRIPTION['name_error'])

    status = homework.get('status', 'status_error')
    if (status == 'status_error') or (status not in VERDICTS):
        raise ValueError(
            ERROR_DESCRIPTION['status_error'].format(
                homework_name=homework_name
            )
        )
    return VERDICTS[status].format(homework_name=homework_name)


def get_homework_statuses(current_timestamp):
    """
    Запросить статус домашки через API.

    Args:
        current_timestamp (int): начало интервала времени

    Returns:
        (dict): в зависимости от ответа возможно:
            {'homeworks': [], 'current_date': 1622751338};
            {'homeworks': [{...},], 'current_date': 1622752114}
    """
    headers = HEADERS
    params = {
        'from_date': current_timestamp
    }

    try:
        homework_statuses = requests.get(
            API_URL,
            headers=headers,
            params=params
        )
    except ConnectionError as err:
        raise ConnectionError(
            ERROR_DESCRIPTION['ConnectionError'].format(err)
        )
    except TimeoutError as err:
        raise TimeoutError(
            ERROR_DESCRIPTION['TimeoutError'].format(err)
        )
    except Exception as err:
        raise Exception(
            ERROR_DESCRIPTION['other_errors'].format(err)
        )

    try:
        resp_json = homework_statuses.json()
    except JSONDecodeError as err:
        raise JSONDecodeError(
            ERROR_DESCRIPTION['JSONDecodeError'].format(err)
        )

    if 'homeworks' in resp_json:
        return resp_json

    raise Exception(
        ERROR_DESCRIPTION['ResponseExcept'].format(
            code=resp_json.get('code', ''),
            message=resp_json.get('message', '')
        )
    )


def send_message(message, bot_client):
    return bot_client.send_message(CHAT_ID, message)


def main():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    file_handler = RotatingFileHandler(
        LOG_PATH_NAME, maxBytes=50000000, backupCount=3
    )
    file_handler.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    t_bot = Bot(token=TELEGRAM_TOKEN)
    logger.debug(LOG_MESSAGES['bot_start'])
    current_timestamp = int(time.time())
    #current_timestamp = 0

    while True:
        try:
            new_homework = get_homework_statuses(current_timestamp)
            homeworks = new_homework.get('homeworks')
            if homeworks:
                message_text = parse_homework_status(homeworks[0])
                send_message(message_text, t_bot)
                logger.info(
                    LOG_MESSAGES['send_message'].format(message=message_text)
                )
            current_timestamp = (
                new_homework.get('current_date', current_timestamp)
                or current_timestamp
            )
            time.sleep(300)

        except Exception as err:
            logger.error(LOG_MESSAGES['bot_error'].format(err=err))
            time.sleep(5)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.ERROR,
        filemode='w',
        format=(
            '%(asctime)s, %(levelname)s, %(name)s, %(filename)s, '
            '%(funcName)s, %(lineno)s, %(message)s'
        )
    )
    main()
