from pathlib import Path
from openpyxl.utils import exceptions
from functions import *

import openpyxl
import os
import requests

mb = 15 * 1048576

# todo: продумать удаление данных, чтобы не скапливались
logger = log_entry("base")


class ParsData:
    """
        Отправка и закрепление за вакансией кандидатов, в сервисе huntflow, средствами api
    """

    print(__doc__)

    base_url = "https://dev-100-api.huntflow.dev"

    def __init__(self, user_token, file_db, file_resume):

        """
            :param str user_token: Пользовательский токен
            :param str file_db: Путь к файлу DB
            :param str file_resume: Путь к папке с резюме
        """

        self.token = user_token
        self.path_in_file_db = file_db
        self.path_in_file_resume = file_resume

        # Заголовк для отправки запросов
        self.header = {
            "User-Agent": "App/1.0 test@huntflow.ru",
            "Authorization": "Bearer %s" % token,
            }

        self.account_id = self.getting_account_id()
        self.status_data = self.getting_status_id()
        self.generated_data = self.getting_data()

    def handle(self):
        self.adding_candidate()

    def getting_account_id(self):

        """
            Получение данных об организации
        """

        url = "%s/accounts" % self.base_url
        data = connect(url, header=self.header, sending_method='GET')
        available_org = []
        if data:
            message = 'You must enter the organization id. \n' \
                      'Available organizations for this token: \n '
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
                    input_org_id = int(input("Enter the organization id: "))
                    if input_org_id in available_org:
                        # self.account_id = input_org_id
                        return input_org_id
                    else:
                        print("There is no such organization in the list, please try again. \n")
                        continue
                except ValueError:
                    print('This is not a number, try again. \n')
                    continue
        else:
            raise SystemExit("No organizations available.")

    def getting_data(self):

        """
            Формирование данных для отправки
        """

        xlsx_file = Path(self.path_in_file_db)
        data = []

        print(
            """
                ####################################
                # Collecting data about candidates #
                ####################################
            """
        )

        try:
            wb_obj = openpyxl.load_workbook(xlsx_file)
            sheet = wb_obj.active

            for row in range(2, sheet.max_row + 1):
                # Данные из базы данных excel
                position_desire = sheet[row][0].value
                full_name = sheet[row][1].value
                wages = sheet[row][2].value
                comment = sheet[row][3].value

                print("Collecting data about %s..." % full_name.strip())

                # Получение id статуса
                status_text = sheet[row][4].value
                status = None
                for status_id, value_status in self.status_data.items():
                    if value_status == str(status_text):
                        status = status_id

                # Получение пути файла
                path_file = self.getting_file_resume(full_name.strip()) or ""

                # Парсинг данных
                result_pars_file = self.sending_file(path_file)
                fields_file = result_pars_file.get("fields", {})
                phone = fields_file.get("phones", [])

                # Получение id вакансий
                vacancies = self.getting_vacancies()
                data.append({
                    # Данные из файла excel
                    "position_desire": position_desire,  # Желаемая должность
                    "full_name": full_name,  # Полное имя
                    "wages": wages,  # Ожидаемая з/п
                    "comment": comment,  # Комментарий
                    "status": status,  # Статус
                    "status_text": status_text,  # Текст статуса

                    # Данные из парсинга резюме
                    "id_resume_file": result_pars_file.get("id", None),  # id загруженного файла
                    "name": fields_file.get("name", {}) or {},
                    "birth_date": fields_file.get("birthdate", {}) or {},
                    "body": result_pars_file.get("text", ""),  # Полный текст резюме
                    "phones": str(phone[0]) if len(phone) >= 1 else "",
                    "email": fields_file.get("email", ""),
                    "position_now": fields_file.get("position", ""),  # Кем работает
                    "photo_id": result_pars_file.get("photo", {}).get("id", None),

                    # id вакансии
                    "vacancies": vacancies.get(position_desire, None)
                })
            wb_obj.close()
        except openpyxl.utils.exceptions.InvalidFileException:
            logger.error("Incorrect path or name of the db file")
            raise SystemExit()

        return data

    def getting_status_id(self):

        """
            Получение id статуса
        """

        url = "%s/account/%s/vacancy/statuses" % (self.base_url, self.account_id)
        status_data = {}
        resp = connect(url, header=self.header, sending_method="GET")
        for item, item_list in resp.items():
            for status_item_data in item_list:
                if status_item_data.get("id", None):
                    status_data[status_item_data.get("id", None)] = status_item_data.get("name", "")

        if not status_data:
            logger.error("No status code")

        return status_data

    def getting_file_resume(self, name_file):

        """
            Получение пути файла
            :param str name_file: Название файла
            :return: путь к файлу
        """

        resume_file = Path(self.path_in_file_resume)
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

            :param str path_in_file: Путь к файлу
            :return dict data_resume: Данные после парсинга документа
        """

        url = "%s/account/%s/upload" % (self.base_url, self.account_id)
        path_file = Path(path_in_file)

        data_resume = connect(url, path_file, header=self.header, sending_method="FILE_POST")
        return data_resume

    def getting_vacancies(self):

        """
            Получение списка вакансий
        """

        url = '%s/account/%s/vacancies' % (self.base_url, self.account_id)
        all_vacancies = {}

        # Получение только активных вакансий
        vacancies = connect(url, param=dict(opened="true"), header=self.header, sending_method="GET")
        for vac_list in vacancies.get("items", {}):
            vac_id = vac_list.get("id", "")
            vac_name = vac_list.get("position", "")
            if vac_name:
                all_vacancies[vac_name] = vac_id

        if all_vacancies:
            return all_vacancies
        else:
            logger.error("There are no vacancies available")
            raise SystemExit()

    def adding_candidate(self):

        """
            Добавление кандидата в базу
        """

        url = "%s/account/%s/applicants" % (self.base_url, self.account_id)

        print(
            """
                #####################################
                # Adding candidates to the database #
                #####################################
            """
        )

        for candidate_data in self.generated_data:
            full_name = candidate_data.get("name", {})
            birth_date = candidate_data.get("birth_date", {})

            data = {
                "last_name": full_name.get("last", ""),
                "first_name": full_name.get("first", ""),
                "middle_name": full_name.get("middle", ""),
                "phone": candidate_data.get("phones", ""),
                "email": candidate_data.get("email", ""),
                "position": candidate_data.get("position_now", ""),  # Кем работает
                "company": "",  # Где работает
                "money": candidate_data.get("wages", ""),  # Зарплатные ожидания
                "birthday_day": birth_date.get("day", ""),
                "birthday_month": birth_date.get("month", ""),
                "birthday_year": birth_date.get("year", ""),
                "photo": candidate_data.get("photo_id", None),  # Фото кандидата (идентификатор загруженного файла)
                "externals": [
                    {
                        "data": {
                            "body": candidate_data.get("body", ""),  # Текст резюме
                        },
                        "auth_type": "NATIVE",  # Тип резюме
                        "files": [
                            {
                                "id": candidate_data.get("id_resume_file", None)  # Идентификатор файла загруженного резюме
                            }
                        ],
                        "account_source": None # Источник резюме
                    }
                ],
            }
            resp = connect(url, data=data, header=self.header, sending_method="POST")

            # id Кандидата
            applicant_id = resp.get("id", None)

            securing_candidate = {
                "vacancy": candidate_data.get("vacancies", None),
                "status": candidate_data.get('status', None),
                "comment": candidate_data.get("comment", ""),
                "files": [
                    {
                        "id": candidate_data.get("id_resume_file", None)
                    }
                ],
            }
            self.adding_candidate_on_vacancy(securing_candidate, applicant_id)
            print("Candidate %s, sent" % candidate_data.get("full_name", "").strip())

    def adding_candidate_on_vacancy(self, securing_candidate, applicant_id):
        """
            Добавление кандидата на вакансию
            :param dict securing_candidate: json для отправки
            :param int applicant_id: id кандидата
        """

        url = "%s/account/%s/applicants/%s/vacancy" % (self.base_url, self.account_id, applicant_id)
        resp = connect(url, data=securing_candidate, header=self.header, sending_method="POST")


def connect(url, path_file=None, header=None, data=None, param=None, sending_method=None):

    """
        Выполнение HTTP запросов, для получения и заполнения данных
        :param str url: Url запроса
        :param str path_file: Путь к файлу
        :param dict header: Заголовок запроса
        :param dict data: Тело запроса
        :param dict param: Параметры запроса
        :param str sending_method: Метод передачи запроса
    """
    success = False
    resp = {}
    if sending_method == "FILE_POST":
        try:
            with open(path_file, 'rb') as file_full:
                sending_files = {'file': ("document_file", file_full, "application/octet-stream")}
                header["X-File-Parse"] = "true"
                try:
                    resp = requests.post(url, headers=header, files=sending_files, timeout=60)
                    success = checking_status(resp.status_code, resp.text)
                except requests.exceptions.Timeout:
                    logger.error("Waiting time exceeded in request post")
        except FileNotFoundError:
            logger.error("There is no file to send or the file path is specified incorrectly.")
            raise SystemExit()
        except TypeError:
            logger.error("The resume file was not found")
            raise SystemExit()

    elif sending_method == "GET":
        try:
            resp = requests.get(url, headers=header, params=param, timeout=60)
            success = checking_status(resp.status_code, resp.text)
        except requests.exceptions.Timeout:
            logger.error("Waiting time exceeded in request post")

    elif sending_method == "POST":
        try:
            resp = requests.post(url, headers=header, json=data, timeout=60)
            success = checking_status(resp.status_code, resp.text)
        except requests.exceptions.Timeout:
            logger.error("Waiting time exceeded in request post")

    if success:
        data_resume = resp.json()
    else:
        logger.error("Empty response to requests")
        raise SystemExit()

    return data_resume


if __name__ == '__main__':
    # Авторизационный токен
    print("Example: 01e89e8af0rwq06575b3w4ae808493jbb6386fe3085o4p23515cbc7b43505084482")
    token = input("Enter the user token: ")
    print(("#" * 50) + "\n")

    # Путь к базе данных .xlsx
    print(r"Example: C:\Users\folder\database.xlsx")
    path_in_file_db = str(input("Enter the path to the database file: "))
    print(("#" * 50) + "\n")

    # Путь к папке с резюме
    print(r"Example: C:\Users\folder")
    path_in_file_resume = str(input("Enter the path to the resume folder: "))
    print(("#" * 50) + "\n")

    instance = ParsData(user_token=token,
                        file_db=path_in_file_db,
                        file_resume=path_in_file_resume)
    instance.handle()
