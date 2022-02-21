import sys
import logging
import requests


def log_entry(name):
    """
    Настройки логирования
    """

    logger_base = logging.getLogger(name)
    logging.basicConfig(filename="logs/errors_file.txt",
                        filemode='a',
                        format='%(asctime)s - %(message)s',
                        datefmt='%d-%m-%y %H:%M:%S')
    console = logging.StreamHandler(stream=sys.stdout)
    logger_base.addHandler(console)
    return logger_base


logger = log_entry("functions")


def checking_status(resp):
    """
    Проверка статуса

    Parameters:
        resp dict: Ответ сервера на запрос

    Returns:
        success bool: Статус проверки
    """

    success = False
    if "errors" in resp:
        logger.error(f"Запрос вернусля с ошибкой {resp.get('errors', '')}")
    else:
        try:
            resp.raise_for_status()
            success = True
        except requests.exceptions.HTTPError as err:
            logger.error(f'error: {err}')

    return success
