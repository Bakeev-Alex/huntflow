import requests

from functions import log_entry
from decorators import success_func

logger = log_entry("connect")


@success_func
def pars_file_from_api(url, header, path_file):
    """
    Отправка post запросом файла для парсинга

    Parameters:
        url str: Url запроса
        header dict: Заголовок запроса
        path_file str: Путь к файлу

    Returns:
        resp dict: Данные ответа
    """

    try:
        with open(path_file, 'rb') as file_full:
            sending_files = {'file': ("document_file", file_full, "application/octet-stream")}
            header["X-File-Parse"] = "true"
            try:
                resp = requests.post(url, headers=header, files=sending_files, timeout=60)
                return resp
            except requests.exceptions.Timeout:
                logger.error("Превышено время ожидания запроса.")
    except FileNotFoundError:
        logger.error(f"Файл {path_file} для отправки отсутствует "
                     f"или путь к указан неправильно.")
    except TypeError:
        logger.error("Файл резюме не был найден.")


@success_func
def request_api_get(url, header, param=None):
    """
    Получение данных через get запрос

    Parameters:
        url str: Url запроса
        header dict: Заголовок запроса
        param dict: Параметры запроса

    Returns:
        resp dict: Данные ответа
    """

    try:
        resp = requests.get(url, headers=header, params=param, timeout=60)
        return resp
    except requests.exceptions.Timeout:
        logger.error('Превышено время ожидания запроса.')


@success_func
def request_api_post(url, header, data):
    """
    Отправка данных пост запросом

    Parameters:
        url str: Url запроса
        header dict: Заголовок запроса
        data dict: Данные запроса

    Returns:
        resp dict: Данные ответа
    """
    try:
        resp = requests.post(url, headers=header, json=data, timeout=60)
        return resp
    except requests.exceptions.Timeout:
        logger.error("Превышено время ожидания запроса.")
