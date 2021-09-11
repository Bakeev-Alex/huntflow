from pathlib import Path
from pprint import pprint

import json
import openpyxl
import os
import logging
import requests

mb = 15 * 1048576

# todo: продумать удаление данных, чтобы не скапливались
logging.basicConfig(filename="logs/send_resume.txt",
                    filemode='a',
                    format='%(asctime)s - %(message)s',
                    datefmt='%d-%m-%y %H:%M:%S')

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
    path_in_file = r"C:\Users\Coffee\Desktop\Тестовое задание\Менеджер по продажам\Корниенко Максим.doc"
    # path_in_file = input("Enter the path to the file: ")

    # Путь к базе данных .xlsx
    __path_in_file_db = r"C:\Users\Coffee\Desktop\Тестовое задание\Тестовая база.xlsx"

    # Путь к папке с резюме
    __path_in_file_resume = r"C:\Users\Coffee\Desktop\Тестовое задание"

    data = []
    path_file = ''

    def handle(self):
        self.getting_data()
        # self.sending_file(self.path_in_file)

    def getting_data(self):
        # FIXME: Обработать ошибки с неправильным путем!
        # FIXME: проверить нужно ли закрыть соединение к документу
        xlsx_file = Path(self.__path_in_file_db)
        wb_obj = openpyxl.load_workbook(xlsx_file)
        sheet = wb_obj.active

        for row in range(2, sheet.max_row + 1):
            position_desire = sheet[row][0].value
            full_name = sheet[row][1].value
            wages = sheet[row][2].value
            comment = sheet[row][3].value
            status = sheet[row][4].value

            path_file = self.getting_file_resume(full_name.strip())

            result_pars_file = self.sending_file(path_file)
            fields_file = result_pars_file.get("fields", {})
            phone = fields_file.get("phones", [])[0]
            # print(result_pars_file)

            self.data.append({
                # Данные из файла excel
                "position_desire": position_desire, # Желаемая должность
                "full_name": full_name, # Полное имя
                "wages": wages, # Ожидаемая з/п
                "comment": comment, # Комментарий
                "status": status, # Статус
                "path_file": path_file, # Путь к резюме (убрать)

                # Данные из парсинга резюме
                "id_resume_file": result_pars_file.get("id", {}),
                "name": fields_file.get("name", {}),
                "birth_date": fields_file.get("birthdate", {}),
                "body": result_pars_file.get("text", ""),
                "phones": phone,
                "email": fields_file.get("email", ""),
                "position_now": fields_file.get("position", ""),
                "photo_id": result_pars_file.get("position", {}).get("id", None),
            })
        wb_obj.close()
        # FIXME: вместо этого вывести ФИО
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
                            logging.error('The file size exceeds the maximum. Name:')
                            continue

        return self.path_file

    def sending_file(self, path_in_file):
        # todo: Обращаться сюда из поиска путей файлов
        url = "%s/account/2/upload" % self.base_url
        path_file = Path(path_in_file)

        data_resume = connect(url, path_file, sending_method="POST")
        return data_resume


def connect(url, path_file, sending_method="GET"):
    if sending_method == "POST":
        try:
            success = True
            with open(path_file, 'rb') as file_full:
                files_test = {'file': ("document_file", file_full, "application/octet-stream")}
                header["X-File-Parse"] = "true"
                try:
                    resp = requests.post(url, headers=header, files=files_test, timeout=60)
                except requests.exceptions.Timeout:
                    logging.error("Waiting time exceeded in requests")
                    success = False
        except FileNotFoundError:
            success = False
            logging.error("There is no file to send or the file path is specified incorrectly. File: %s" % path_file)

        if success:
            data_resume = resp.json()
        else:
            data_resume = {}
            print('Add logs')

        return data_resume

    else:
        resp = requests.get(url)


if __name__ == '__main__':
    ParsData().handle()
