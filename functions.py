import sys
import logging
import requests


def log_entry(name):
    """
    Настройки логирования
    """

    root_logger = logging.getLogger(name)
    logging.basicConfig(handlers=[logging.FileHandler('logs/errors_file.txt', 'w', 'utf-8')],
                        format='%(asctime)s - %(message)s',
                        datefmt='%d-%m-%y %H:%M:%S')
    console = logging.StreamHandler(stream=sys.stdout)
    root_logger.addHandler(console)
    return root_logger


logger = log_entry("functions")


def checking_status(resp) -> bool:
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
