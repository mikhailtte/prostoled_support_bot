# параметры для запуска бота
TOKEN = '6002588353:AAF4KfN1So2FMlG7M2nSs-rBfX-YRnTK8Oo'
CHAT_ID = -1001778869911

CERT = '/home/mikhailtte/certs/cert.pem'
WEBHOOK_HOST = 'https://185.116.193.204:443'
WEBHOOK_PATH = TOKEN
WEBHOOK_URL = f"{WEBHOOK_HOST}/{WEBHOOK_PATH}"
WEBAPP_HOST = '0.0.0.0.'  # or ip
WEBAPP_PORT = 8000
LOG_FILE = 'logging.log'
TOKEN = '6002588353:AAF4KfN1So2FMlG7M2nSs-rBfX-YRnTK8Oo'

# обновление webhook
# https://api.telegram.org:443/botTOKEN/setWebhook?url=https://IP:PORT/TOKEN
# Для запуска необходимо запустить nginx сервер c перенаправлением входящих
# внешних подключений на соответствущий внутреннее подключение на котором
# будет работать данное веб-приложение.
# Затем запустить само приложение обычной коммандой python. 