from functions import checking_status


def success_func(func):
    """
    Проверка статуса и получение данных

    Returns:
        data_resume dict: словарь с данными запроса
    """

    def wrapper(*args, **kwargs):
        resp = func(*args, **kwargs)
        success = checking_status(resp)
        if success:
            data_resume = resp.json()
        else:
            data_resume = {}
        return data_resume
    return wrapper
