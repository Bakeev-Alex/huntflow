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


class ParsData:
    """
        Получение и парсинг данных
    """

    # todo: продумать куда записывать отправленых кандидатов, либо база или что-то подобное.
    print(__doc__)

    # Авторизационный токен
    # __token = input("Enter the user token: ")
    __token = "71e89e8af02206575b3b4ae80bf35b6386fe3085af3d4085cbc7b43505084482"

    # Путь к файлу
    path_in_file = r"C:\Users\Coffee\Desktop\Тестовое задание\Менеджер по продажам\Корниенко Максим.do"
    # path_in_file = input("Enter the path to the file: ")

    # Путь к базе данных .xlsx
    __path_in_file_db = r"C:\Users\Coffee\Desktop\Тестовое задание\Тестовая база.xlsx"

    # Путь к папке с резюме
    __path_in_file_resume = r"C:\Users\Coffee\Desktop\Тестовое задание"
    data = []
    path_file = ''

    def handle(self):
        # self.getting_data_in_xlsx()
        self.sending_file(self.path_in_file)

    def getting_data_in_xlsx(self):
        # FIXME: Обработать ошибки с неправильным путем!
        xlsx_file = Path(self.__path_in_file_db)
        wb_obj = openpyxl.load_workbook(xlsx_file)
        sheet = wb_obj.active

        for row in range(2, sheet.max_row + 1):
            position = sheet[row][0].value
            full_name = sheet[row][1].value
            wages = sheet[row][2].value
            comment = sheet[row][3].value
            status = sheet[row][4].value
            path_file = self.getting_file_resume(full_name.strip())

            self.data.append({
                "position": position,
                "full_name": full_name,
                "wages": wages,
                "comment": comment,
                "status": status,
                "path_file": path_file
            })
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
        url = "https://dev-100-api.huntflow.dev/account/2/upload"
        # url = "http://httpbin.org/post"
        # FIXME: Вынести в base_header и добавлять в него необходимые ключи
        header = {
            "User-Agent": "App/1.0 test@huntflow.ru",
            "X-File-Parse": "true",
            "Authorization": "Bearer %s" % self.__token,
        }

        # FIXME: при парсенге, нужно будет формировать путь, чтобы отправить
        path_file = Path(path_in_file)

        try:
            success = True
            with open(path_file, 'rb') as file_full:
                files_test = {'file': ("test.doc", file_full, "application/octet-stream")}
                try:
                    resp = requests.post(url, headers=header, files=files_test, timeout=60)
                except requests.exceptions.Timeout:
                    logging.error("Waiting time exceeded in requests")
                    success = False
        except FileNotFoundError:
            success = False
            logging.error("There is no file to send or the file path is specified incorrectly. File: Имя файла из json")

        if success:
            data_resume = json.dumps(resp.json(), indent=4, ensure_ascii=False)
        else:
            print('Add logs')


if __name__ == '__main__':
    ParsData().handle()
