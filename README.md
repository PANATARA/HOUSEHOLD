## You need to configure your .env file inroot directory

```env
PG_DATABASE=postgres
PG_USER=postgres
PG_PASSWORD=postgres
redis_url=redis://redis:6379
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres_db:5432/postgres
SECRET_KEY=mySecretKey
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_MINUTES=20160
S3_ACCESS_KEY=myS3AccessKey
S3_SECRET_KEY=myS3SecretKey
S3_ENDPOINT_URL=https://mys3.endpoint.url
S3_BUCKET_NAME=household-storage
EMAIL_ADDRESS=email@example.ru
EMAIL_PASSWORD=password
EMAIL_HOSTNAME=smtp.email.ru
```

## Тестирование (Running Tests)

Все зависимости для тестирования вынесены в `requirements-dev.txt`, благодаря чему продакшен-окружение (`requirements.txt`) остаётся чистым и легковесным.
Тесты полностью изолированы и используют моки, поэтому не требуют запущенной базы данных, Redis или RabbitMQ, а выполняются за доли секунды (~0.2 сек).

### Запуск тестов локально:
```bash
# Установка dev-зависимостей (если ещё не установлены)
pip install -r requirements-dev.txt

# Быстрый запуск всех тестов
pytest

# Запуск с подробным выводом
pytest -v
```

### Запуск через Docker (Dockerfile.test):
```bash
docker build -f Dockerfile.test -t household-test .
docker run --rm household-test pytest
```
