from pathlib import Path
from openpyxl.utils import exceptions
from functions import *

import json
import openpyxl
import os
import requests
import sys

mb = 15 * 1048576

# todo: продумать удаление данных, чтобы не скапливались
logger = log_entry("base")

"""
    Получение данных от пользователя, токена и путь к базе .xlsx
"""

# Авторизационный токен
# __token = input("Enter the user token: ")
__token = ""

# Заголовк для отправки запросов
header = {
    "User-Agent": "App/1.0 test@huntflow.ru",
    "Authorization": "Bearer %s" % __token,
}


class ParsData:
    """
        Получение и парсинг данных
    """

    # todo: продумать куда записывать отправленых кандидатов, либо база или что-то подобное.
    print(__doc__)

    base_url = "https://dev-100-api.huntflow.dev"

    # Путь к файлу
    # path_in_file = r"C:\Users\Coffee\Desktop\Тестовое задание\Менеджер по продажам\Корниенко Максим.doc"
    path_in_file = r"/home/alex/Загрузки/Тестовое задание/Менеджер по продажам/Корниенко Максим.doc"
    # path_in_file = input("Enter the path to the file: ")

    # Путь к базе данных .xlsx
    # __path_in_file_db = r"C:\Users\Coffee\Desktop\Тестовое задание\Тестовая база.xlsx"
    __path_in_file_db = r"/home/alex/Загрузки/Тестовое задание/Тестовая база.xlsx"

    # Путь к папке с резюме
    # __path_in_file_resume = r"C:\Users\Coffee\Desktop\Тестовое задание"
    __path_in_file_resume = r"/home/alex/Загрузки/Тестовое задание"

    data = []
    path_file = ''

    def __init__(self):
        self.account_id = self.getting_account_id()

    def handle(self):
        self.getting_data()
        # self.sending_file(self.path_in_file)
        # self.getting_vacancies()

    def getting_account_id(self):

        """
            Получение данных об организации
        """

        # FIXME: Поменять все русское на англ
        url = "%s/accounts" % self.base_url
        data = connect(url, sending_method='GET')
        available_org = []
        if data:
            message = 'Необходимо ввести id организации. \n' \
                      'Доступные организации этому токену: \n '
            for key, value in data.items():
                for organization in value:
                    organization = dict(organization)
                    org_id = organization.get('id', '')
                    org_name = organization.get('name', '')
                    message += f'"{org_name}": {org_id} \n'
                    available_org.append(org_id)
            print(message)

            while available_org:
                try:
                    input_org_id = int(input("Введите id организацию: "))
                    if input_org_id in available_org:
                        # self.account_id = input_org_id
                        return input_org_id
                    else:
                        print("Такой организации нет в списке, попробуйте еще раз. \n")
                        continue
                except ValueError:
                    print('Вы ввели не число, попробуйте еще раз. \n')
                    continue
        else:
            raise SystemExit("Нет доступных организайций")

    def getting_data(self):

        """
            Формирование данных для отправки
        """

        xlsx_file = Path(self.__path_in_file_db)
        try:
            wb_obj = openpyxl.load_workbook(xlsx_file)
            sheet = wb_obj.active

            for row in range(2, sheet.max_row + 1):
                # Данные из базы данных excel
                position_desire = sheet[row][0].value
                full_name = sheet[row][1].value
                wages = sheet[row][2].value
                comment = sheet[row][3].value
                status = sheet[row][4].value

                path_file = self.getting_file_resume(full_name.strip())

                # Данные из парсинга
                result_pars_file = self.sending_file(path_file)
                fields_file = result_pars_file.get("fields", {})
                phone = str(fields_file.get("phones", []))

                # Получение id вакансий
                vacancies = self.getting_vacancies()

                self.data.append({
                    # Данные из файла excel
                    "position_desire": position_desire, # Желаемая должность
                    "full_name": full_name, # Полное имя
                    "wages": wages, # Ожидаемая з/п
                    "comment": comment, # Комментарий
                    "status": status, # Статус

                    # Данные из парсинга резюме
                    "id_resume_file": result_pars_file.get("id", {}),
                    "name": fields_file.get("name", {}),
                    "birth_date": fields_file.get("birthdate", {}),
                    "body": result_pars_file.get("text", ""),
                    "phones": phone,
                    "email": fields_file.get("email", ""),
                    "position_now": fields_file.get("position", ""),
                    "photo_id": result_pars_file.get("position", {}).get("id", None),

                    # id вакансии
                    "vacancies": vacancies[position_desire]
                })
            wb_obj.close()
        except openpyxl.utils.exceptions.InvalidFileException:
            logger.error("Incorrect path or name of the db file")

        print(json.dumps(self.data, indent=4, ensure_ascii=False))
        return self.data

    def getting_file_resume(self, name_file):

        """
        Получение пути файла
        :param name_file: Название файла
        :return: путь к файлу
        """

        resume_file = Path(self.__path_in_file_resume)
        if name_file:
            for root, dirs, files in os.walk(resume_file):
                for file in files:
                    if file.startswith(name_file):
                        size_file = Path(os.path.join(root, file)).stat().st_size
                        if size_file <= mb:
                            self.path_file = os.path.join(root, file)
                        else:
                            logger.error('The file size exceeds the maximum. Name:')
                            continue

        return self.path_file

    def sending_file(self, path_in_file):

        """
            Возвращает данные после парсинга на сервесе huntflow через api
        """

        url = "%s/account/%s/upload" % (self.base_url, self.account_id)
        path_file = Path(path_in_file)

        data_resume = connect(url, path_file, sending_method="POST")
        return data_resume

    def getting_vacancies(self):
        url = '%s/account/%s/vacancies' % (self.base_url, self.account_id)
        all_vacancies = {}

        # Получение только активных вакансий
        vacancies = connect(url, param=str(dict(opened="true")), sending_method="GET")
        for vac_list in vacancies.get("items", {}):
            vac_id = vac_list.get("id", "")
            vac_name = vac_list.get("position", "")
            if vac_name:
                all_vacancies[vac_name] = vac_id

        return all_vacancies


def connect(url, path_file=None, param="", sending_method=""):

    """
        Выполнение HTTP запросов, для получения и заполнения данных
    """
    success = False
    resp = {}
    if sending_method == "POST":
        try:
            # FIXME: Проверить с установленным None
            with open(path_file, 'rb') as file_full:
                files_test = {'file': ("document_file", file_full, "application/octet-stream")}
                header["X-File-Parse"] = "true"
                try:
                    resp = requests.post(url, headers=header, files=files_test, timeout=60)
                    success = checking_status(resp.status_code, resp.text)
                except requests.exceptions.Timeout:
                    logger.error("Waiting time exceeded in request post")
        except FileNotFoundError:
            logger.error("There is no file to send or the file path is specified incorrectly. File: %s")

    elif sending_method == "GET":
        try:
            resp = requests.get(url, headers=header, params=param, timeout=60)
            success = checking_status(resp.status_code, resp.text)
        except requests.exceptions.Timeout:
            logger.error("Waiting time exceeded in request post")

    if success:
        data_resume = resp.json()
    else:
        data_resume = {}
        logger.error("Empty response to requests")

    return data_resume


if __name__ == '__main__':
    ParsData().handle()
