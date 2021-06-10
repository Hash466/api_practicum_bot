import logging
import os
import sys
import time
from json import JSONDecodeError
from logging.handlers import RotatingFileHandler

import requests
from dotenv import load_dotenv
from telegram import Bot

LOG_FILENAME = 't_bot.log'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH_NAME = os.path.join(BASE_DIR, LOG_FILENAME)
logging.basicConfig(
    level=logging.INFO,
    # filename=LOG_PATH_NAME,
    handlers=[
        RotatingFileHandler(
            LOG_PATH_NAME, maxBytes=50000000, backupCount=3
        )
    ],
    # filemode='w',
    format=(
        '%(asctime)s, %(levelname)s, %(name)s, %(filename)s, '
        '%(funcName)s, %(lineno)s, %(message)s'
    )
)
LOG_MESSAGES = {
    'send_message': 'Отправлено сообщение: {message}',
    'bot_start': 'Бот запущен!',
    'bot_error': 'Бот столкнулся с ошибкой!:\n{err}',
    'env_error': 'При получении данных из .env возникла ошибка:\n{err}',
}

ERROR_DESCRIPTION = {
    'ConnectionError': 'Ошибка соединения!\n{err}',
    'TimeoutError': 'Время ожидание ответа истекло!\n{err}',
    'JSONDecodeError': 'Ошибка разбора json ответа сервера!\n{err}',
    'ResponseExcept': 'Ответ API содержит ошибку "{code}" {message}',
    'evn_error': 'Ошибка загрузки данных из ".env": {err}',
    'status_error': 'Недокументированный статус работы: "{homework_name}"!',
    'name_error': 'Отсутствует имя домашки!',
    'other_errors': 'При попытке подключения к API произошла ошибка:\n{err}'
}

VERDICTS = {
    'rejected': ('У вас проверили работу "{homework_name}"!\n'
                 'К сожалению в работе нашлись ошибки.'),
    'approved': ('У вас проверили работу "{homework_name}"!\n'
                 'Ревьюеру всё понравилось, можно приступать к следующему '
                 'уроку.'),
    'reviewing': ('Ваша работа "{homework_name}" в данный момент проходит '
                  'ревью.\nМолитесь всем Богам, или предложите ревьюверу '
                  'бутылочку нормального пойла, дабы задобрить уважаемого!'
                  '\nЕсли, конечно, ревьювер не трезвенник!!!'),
}

load_dotenv()

try:
    PRAKTIKUM_TOKEN = os.environ['PRAKTIKUM_TOKEN']
    TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
    CHAT_ID = os.environ['TELEGRAM_CHAT_ID']
except KeyError as err:
    logging.exception(LOG_MESSAGES['env_error'].format(err=err))
    sys.exit(1)

HEADERS = {'Authorization': f'OAuth {PRAKTIKUM_TOKEN}'}
API_URL = 'https://praktikum.yandex.ru/api/user_api/homework_statuses/'


def parse_homework_status(homework):
    """
    Разобрать ответ API.

    Args:
        homework (dict): данные с описанием, статусом и т.п. домашки:

    Returns:
        (str): сообщение с текущим статусом домашки
    """
    homework_name = homework.get('homework_name')
    if not homework_name:
        raise ValueError(ERROR_DESCRIPTION['name_error'])

    status = homework.get('status')
    if status and (status not in VERDICTS):
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
    params = {
        'from_date': current_timestamp
    }

    try:
        homework_statuses = requests.get(
            API_URL,
            headers=HEADERS,
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
    t_bot = Bot(token=TELEGRAM_TOKEN)
    logging.debug(LOG_MESSAGES['bot_start'])

    current_timestamp = int(time.time())

    while True:
        try:
            new_homework = get_homework_statuses(current_timestamp)
            homeworks = new_homework.get('homeworks')
            if homeworks:
                message_text = parse_homework_status(homeworks[0])
                send_message(message_text, t_bot)
                logging.info(
                    LOG_MESSAGES['send_message'].format(message=message_text)
                )
            current_timestamp = (
                new_homework.get('current_date', current_timestamp)
                or current_timestamp
            )
            time.sleep(300)

        except Exception as err:
            err_msg = LOG_MESSAGES['bot_error'].format(err=err)
            logging.error(err_msg)
            send_message(err_msg, t_bot)
            time.sleep(60)


if __name__ == '__main__':
    main()
