import openpyxl
import os

from pathlib import Path
from openpyxl.utils import exceptions

from functions import log_entry
from connect import request_api_get, pars_file_from_api, request_api_post

mb = 15 * 1048576

logger = log_entry("base")


# FixMe: Прописать типизацию

# FixMe: Посмотреть где можно убрать списки и заменить кортежами

class ParsData:
    """
        Отправка и закрепление за вакансией кандидатов, в сервисе huntflow, средствами api
    """

    base_url = "https://dev-100-api.huntflow.dev"

    def __init__(self, user_token, file_db, file_resume):
        """
        Parameters:
            user_token str: Пользовательский токен
            file_db str: Путь к файлу DB
            file_resume str: Путь к папке с резюме
        """

        self.token = user_token
        self.path_in_file_db = file_db
        self.path_in_file_resume = file_resume

        # Заголовк для отправки запросов
        self.header = {
            "User-Agent": "App/1.0 test@huntflow.ru",
            "Authorization": f"Bearer {token}",
            }

        self.organization_id = self.get_organization_id()
        self.status_data = self.get_statuses()
        self.vacancies = self.get_vacancies()

    def handle(self):
        self.send_data()

    def get_organization_id(self):
        """
        Получение данных об организации

        Returns:
            id_organization int: id организации
        """

        url = f"{self.base_url}/accounts"
        data = request_api_get(url, header=self.header)
        if data:
            available_org = ()
            for key, value in data.items():
                available_org = (id_.get('id') for id_ in value)

            id_organization = next(iter(available_org), None)
            if id_organization:
                return id_organization
            else:
                raise SystemExit("Нет доступных организаций.")
        else:
            raise SystemExit("Запрос не вернул никаких данных.")

    def get_statuses(self):
        """
        Получение статусов организации

        Returns:
            status_data dict: Статусы организации:
                - key: Название статуса
                - value: id статуса

        """

        url = f"{self.base_url}/account/{self.organization_id}/vacancy/statuses"
        status_data = {}
        resp = request_api_get(url, header=self.header)
        for item, item_list in resp.items():
            for status_item_data in item_list:
                id_ = status_item_data.get("id", None)
                if id_:
                    status_data[status_item_data.get("name", "")] = id_

        if not status_data:
            logger.error("Статусы отсутствуют.")

        return status_data

    def get_path_file_resume(self, name_file):
        """
        Поиск файла в папке по названиею.

        Parameters:
            name_file str: Название файла в папке.

        Returns:
            path_file str: Путь к файлу.
        """

        resume_file = Path(self.path_in_file_resume)
        if name_file:
            for root, dirs, files in os.walk(resume_file):
                for file in files:
                    if file.startswith(name_file):
                        size_file = Path(os.path.join(root, file)).stat().st_size
                        if size_file <= mb:
                            path_file = os.path.join(root, file)
                            return path_file
                        else:
                            logger.error('Размер файла превышает максимальный.')
                            continue

    def get_vacancies(self):
        """
        Парсинг вакансий организации.

        Returns:
            all_vacancies dict: Отфильтрованный словарь вакансий:
                - key: Название вакансии
                - values: id вакансии.
        """

        url = f'{self.base_url}/account/{self.organization_id}/vacancies'
        all_vacancies = {}

        success_page = True
        page = 1

        while success_page:
            vacancies = request_api_get(url, param=dict(opened="true", page=page), header=self.header)
            if vacancies.get("items"):
                for vac_list in vacancies.get("items", {}):
                    vac_id = vac_list.get("id", "")
                    vac_name = vac_list.get("position", "")
                    if vac_name:
                        all_vacancies[vac_name] = vac_id
                page += 1
            else:
                success_page = False

        if all_vacancies:
            return all_vacancies
        else:
            logger.error("Свободных вакансий нет")
            raise SystemExit()

    def parse_file(self, path_in_file):
        """
        Возвращает данные после парсинга.

        Parameters:
            path_in_file str: Путь к файлу.

        Return:
            data_resume dict: Данные после парсинга документа.
        """

        url = f"{self.base_url}/account/{self.organization_id}/upload"
        path_file = Path(path_in_file)

        data_resume = pars_file_from_api(url, self.header, path_file)
        return data_resume

    def send_data(self):
        """
        Сбор и передача данных о кандидатах.
        """

        xlsx_file = Path(self.path_in_file_db)

        try:
            wb_obj = openpyxl.load_workbook(xlsx_file)
            sheet = wb_obj.active

            for row in range(2, sheet.max_row + 1):
                # Данные из базы данных excel.
                position_desire = sheet[row][0].value
                full_name = sheet[row][1].value
                wages = sheet[row][2].value
                comment = sheet[row][3].value

                print(f"Сбор данных о {full_name.strip()}...")

                # Получение id статуса.
                status_text = sheet[row][4].value

                # Получение пути файла.
                path_file = self.get_path_file_resume(full_name.strip()) or ""

                # Парсинг данных.
                result_pars_file = self.parse_file(path_file)
                fields_file = result_pars_file.get("fields", {})
                phone = fields_file.get("phones", [])

                # Словари, полученные с парсинга.
                birth_date = fields_file.get("birthdate", {}) or {}
                name_candidate = fields_file.get("name", {}) or {}

                candidate_data = {
                    "last_name": name_candidate.get("last", ""),
                    "first_name": name_candidate.get("first", ""),
                    "middle_name": name_candidate.get("middle", ""),
                    "phone": str(phone[0]) if len(phone) >= 1 else "",
                    "email": fields_file.get("email", ""),
                    "position": fields_file.get("position", ""),  # Кем работает
                    "company": "",  # Где работает
                    "money": wages,  # Ожидаемая з/п
                    "birthday_day": birth_date.get("day", ""),
                    "birthday_month": birth_date.get("month", ""),
                    "birthday_year": birth_date.get("year", ""),
                    "photo": result_pars_file.get("photo", {}).get("id", None),  # Фото кандидата (идентификатор загруженного файла)
                    "externals": [
                        {
                            "data": {
                                "body": result_pars_file.get("text", ""),  # Текст резюме
                            },
                            "auth_type": "NATIVE",  # Тип резюме
                            "files": [
                                {
                                    "id": result_pars_file.get("id", None)
                                    # Идентификатор файла загруженного резюме
                                }
                            ],
                            "account_source": None  # Источник резюме
                        }
                    ],
                }

                applicant_id = self.add_candidate(candidate_data)

                securing_candidate = {
                    "vacancy": self.vacancies.get(position_desire, None),
                    "status": self.status_data.get(str(status_text)),
                    "comment": comment,
                    "files": [
                        {
                            "id": result_pars_file.get("id", None)
                        }
                    ],
                }

                candidate_on_vacancy = self.add_candidate_on_vacancy(securing_candidate, applicant_id)

                if candidate_on_vacancy:
                    print(f"Кандидат {full_name}, добавлен.")
                else:
                    logger.error(f'Запись кандидата на вакансию {full_name} не удалась.')

            wb_obj.close()

        except openpyxl.utils.exceptions.InvalidFileException:
            logger.error("Неверный путь или имя файла базы данных.")
            raise SystemExit()

    def add_candidate(self, candidate_data):
        """
        Отправляет данные кандидата в базу.

        Parameters:
            candidate_data dict: Данные о кандидате для отправки в базу.

        Return:
            candidate_id int: id кандидата в базе.
        """
        # FIXME: Добавить обработку неотправленных заказов
        url = f"{self.base_url}/account/{self.organization_id}/applicants"

        resp = request_api_post(url, header=self.header, data=candidate_data)

        candidate_id = resp.get("id", None)

        return candidate_id

    def add_candidate_on_vacancy(self, securing_candidate, applicant_id):
        """
        Добавление кандидата на вакансию.

        Parameters:
            securing_candidate dict: Данные для отправки.
            applicant_id int: Полученный id кандидата, после записи в базу.

        Returns:
            vacancy_id int: id привязки пользователя на вакансию.
        """

        url = f"{self.base_url}/account/{self.organization_id}/applicants/{applicant_id}/vacancy"
        resp = request_api_post(url, header=self.header, data=securing_candidate)

        vacancy_id = resp.get("id", None)

        return vacancy_id


if __name__ == '__main__':
    # Авторизационный токен
    # print("Example: 01e89e8af0rwq06575b3w4ae808493jbb6386fe3085o4p23515cbc7b43505084482")
    # print("Example: 71e89e8af02206575b3b4ae80bf35b6386fe3085af3d4085cbc7b43505084482")
    # token = input("Enter the user token: ")
    # print(("#" * 50) + "\n")

    # Путь к базе данных .xlsx
    # print(r"Example: C:\Users\folder\database.xlsx")
    # print(r"Example: C:\project\huntflow\files\db_test.xlsx")
    # path_in_file_db = str(input("Enter the path to the database file: "))
    # print(("#" * 50) + "\n")
    #
    # # Путь к папке с резюме
    # print(r"Example: C:\Users\folder")
    # path_in_file_resume = str(input("Enter the path to the resume folder: "))
    # print(("#" * 50) + "\n")

    token = '71e89e8af02206575b3b4ae80bf35b6386fe3085af3d4085cbc7b43505084482'
    path_in_file_resume = r'C:\project\huntflow\files'
    path_in_file_db = r'C:\project\huntflow\files\db_test.xlsx'

    instance = ParsData(user_token=token,
                        file_db=path_in_file_db,
                        file_resume=path_in_file_resume)
    instance.handle()
