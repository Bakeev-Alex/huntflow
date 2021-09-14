# Huntflow 

***

## Этапы работы

1. Получение организаций, проверка токена, если не валиден выводится предупреждение (логируется)
2. Вывод пользователю организаций для выбора, для получения account_id
3. Парсинг БД excel
4. Получение названия файлов, поиск и парсинг через api
5. Получение id статусов для формирования данных
6. Добавление кандидатов в базу с прикреплением файлов резюме 
7. Получение id вакансий для добавления кандидатов
8. Добавление кандидата на вакансию

Версия python 3.8

***

## Запуск:

1. Введите индивидуальный токен
2. Введите полный путь к файлу с базой данных (.xlsx)
3. Введите полный путь к папке с резюме (Чем точнее будет папка с документами тем быстрее будет осуществляться поиск)
4. Выберите организацию из списка, для работы с вакансиями

***

## Errors:
Все ошибки записываются в файл \logs\errors_file.txt.