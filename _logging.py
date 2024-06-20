import logging
from parameters import LOG_FILE

LOG_LEVEL = logging.ERROR

def setup_logger(_LOG_FILE):
    # создаем логгер
    logger = logging.getLogger(__name__)
    logger.setLevel(LOG_LEVEL)

    # Создание обработчика для записи логов в файл
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(LOG_LEVEL)

    # Создание форматтера для определения формата записи логов
    formatter = logging.Formatter('%(asctime)s : %(module)s.%(levelname)s : %(message)s', '%d.%m.%Y %H:%M:%S (%z)')
    file_handler.setFormatter(formatter)

    # Добавление обработчика к логгеру
    logger.addHandler(file_handler)

    return logger

# Пример использования логгера
# logger = setup_logger('app.log')
