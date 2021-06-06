from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
import os
import requests
import time
from telegram import Bot


load_dotenv()

API_URL = 'https://praktikum.yandex.ru/api/user_api/homework_statuses/'
PRAKTIKUM_TOKEN = os.getenv("PRAKTIKUM_TOKEN")
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

LOG_FILENAME = 't_bot.log'
LOG_PATH_NAME = os.sep.join([os.getcwd(), LOG_FILENAME])

VERDICTS = {
    'rejected': ('У вас проверили работу "{homework_name}"!\n'
                 'К сожалению в работе нашлись ошибки.'),
    'approved': ('У вас проверили работу "{homework_name}"!\n'
                 'Ревьюеру всё понравилось, можно приступать к следующему '
                 'уроку.'),
    'reviewing': ('Ваша работа "{homework_name}" в данный момент проходит '
                  'ревью.\nМолитесь всем Богам, или предложите ревьюверу '
                  'бутылочку нормального пойла, дабы задобрить уважаемого!'),
    'status_error': 'Недокументированный статус работы "{homework_name}"!'
}

ERROR_DESCRIPTION = {
    'ConnectionError': 'Ошибка соединения!\n{err}',
    'TimeoutError': 'Время ожидание ответа истекло!\n{err}',
    'ExceptionJson': 'Ошибка разбора json ответа сервера!\n{err}',
    'ResponseExcept': 'Ответ API содержит ошибку!\n{code}\n{message}',
}

LOG_MESSAGES = {
    'message_send': 'Отправлено сообщение: {message}',
    'bot_start': 'Бот запущен!',
    'bot_error': 'Бот столкнулся с ошибкой!:\n{err}',
}


def parse_homework_status(homework):
    """
    разобрать ответ API

    Args:
        homework (dict): данные с описанием, статусом и т.п. домашки:

    Returns:
        (str): сообщение с текущим статусом домашки
    """
    homework_name = homework.get('homework_name', 'имя домашки не задано')
    status = homework.get('status', 'status_error')
    if status == 'status_error':
        raise ValueError(
            VERDICTS[status].format(homework_name=homework_name)
        )
    return VERDICTS[status].format(homework_name=homework_name)


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

    try:
        resp_json = homework_statuses.json()
    except Exception as err:
        raise Exception(
            ERROR_DESCRIPTION['ExceptionJson'].format(err)
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
    logger.setLevel(logging.DEBUG)

    file_handler = RotatingFileHandler(
        LOG_PATH_NAME, maxBytes=50000000, backupCount=3
    )
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    t_bot = Bot(token=TELEGRAM_TOKEN)
    logger.debug(LOG_MESSAGES['bot_start'])
    current_timestamp = (int(time.time()) - (5 * 60))

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
            current_timestamp = new_homework.get('current_date',
                                                 current_timestamp)
            time.sleep(300)

        except Exception as err:
            logger.error(LOG_MESSAGES['bot_error'].format(err=err))
            time.sleep(5)


if __name__ == '__main__':

    log_path = os.getcwd() + os.sep

    logging.basicConfig(
        level=logging.ERROR,
        filename=LOG_PATH_NAME,
        filemode='w',
        format=(
            '%(asctime)s, %(levelname)s, %(name)s, %(filename)s, '
            '%(funcName)s, %(lineno)s, %(message)s'
        )
    )
    main()
