# 🏠 HOUSEHOLD Backend

Бэкенд сервиса управления семейным бытом и задачами. Построен на FastAPI, PostgreSQL, SQLAlchemy (asyncio), Alembic, Redis и ARQ.

---

## ⚡ Быстрый запуск для нового разработчика

Для запуска проекта достаточно скопировать примеры конфигурационных файлов и запустить Docker Compose:

```bash
# 1. Склонировать репозитории бэкенда и приложения
git clone <url_household> HOUSEHOLD
git clone <url_household_app> HOUSEHOLD-APP

# 2. Перейти в папку бэкенда
cd HOUSEHOLD

# 3. Скопировать конфигурационный файл окружения
cp .env.example .env

# 4. Запустить все сервисы (PostgreSQL, Redis, FastAPI, ARQ Worker)
make up
# или: docker compose up -d --build

# 5. Применить миграции базы данных
make migrate

# 6. (Опционально) Заполнить базу начальными шаблонами задач
make seed
```

Бэкенд будет доступен по адресу: **http://localhost:8000**  
Swagger документация API: **http://localhost:8000/docs**

---

## 🔐 Секретные файлы и токены (Таблица соответствия)

В репозитории подготовлены файлы-примеры (`.example`). Чтобы приложение заработало у любого пользователя, нужно просто заполнить их и переименовать:

| Назначение | Файл с примером | Рабочий файл | Обязателен? | Где взять / как получить |
| :--- | :--- | :--- | :---: | :--- |
| **Переменные бэкенда** | [`.env.example`](file://.env.example) | `.env` | **Да** | Скопировать `cp .env.example .env`. Все дефолтные значения уже настроены для работы в Docker. |
| **Секретный ключ JWT** | [`.env.example`](file://.env.example) (`SECRET_KEY`) | `.env` | **Да** | Сгенерировать командой `openssl rand -hex 32` или оставить дефолтный для локальной разработки. |
| **Google Web Client ID** | [`.env.example`](file://.env.example) (`GOOGLE_CLIENT_ID`) | `.env` | Для входа через Google | В [Google Cloud Console](https://console.cloud.google.com/apis/credentials) -> *Create Credentials* -> *OAuth client ID* (тип: **Web application**). |
| **Ключ Firebase Admin** | [`serviceAccountKey.json.example`](file://serviceAccountKey.json.example) | `serviceAccountKey.json` | Для Push-уведомлений | В [Firebase Console](https://console.firebase.google.com/) -> *Project Settings* -> вкладка *Service accounts* -> кнопка **Generate new private key**. Положить файл в корень `HOUSEHOLD/`. |
| **Переменные фронтенда** | `../HOUSEHOLD-APP/frontend/.env.example` | `../HOUSEHOLD-APP/frontend/.env` | Для входа через Google | Скопировать и указать тот же `VITE_GOOGLE_CLIENT_ID`. |
| **Конфиг Firebase Android** | `../HOUSEHOLD-APP/app/google-services.json.example` | `../HOUSEHOLD-APP/app/google-services.json` | Для сборки Android APK | В Firebase Console -> *Project Settings* -> *General* -> скачать `google-services.json`. |

---

## 🔑 Аутентификация в приложении

В системе реализованы следующие способы авторизации (вся старая логика отправки кодов на email полностью удалена):

1. **Логин и пароль**:
   * Регистрация: `POST /api/auth/register` (логин, пароль от 6 символов, имя).
   * Вход: `POST /api/auth/login` (логин и пароль).
   * Пароли хешируются через безопасный алгоритм `bcrypt`.
2. **Google Sign-In / One Tap**:
   * Эндпоинт: `POST /api/auth/google`.
   * Принимает криптографический ID-токен от Google Identity Services, проверяет подпись Google и автоматически создаёт или обновляет пользователя (upsert).
3. **Обновление токенов (Refresh)**:
   * Эндпоинт: `POST /api/auth/refresh`.
4. **Dev / Debug авторизация**:
   * Эндпоинт: `POST /api/auth/debug-auth`.
   * Позволяет мгновенно войти или создать тестового пользователя без ввода пароля при разработке.

---

## 🛠 Полезные команды (Makefile)

```bash
make up           # Запустить все контейнеры в фоне
make down         # Остановить все контейнеры
make restart      # Перезапустить контейнеры
make migrate      # Применить миграции базы данных (alembic upgrade head)
make migration msg="текст"  # Сгенерировать новую миграцию Alembic
make seed         # Загрузить базовые задачи в БД
make logs-app     # Смотреть логи FastAPI бэкенда
make test         # Запустить все unit-тесты (pytest)
make pwa-build    # Собрать PWA из репозитория фронтенда и скопировать в static/
```

---

## 🧪 Тестирование

Тесты полностью изолированы и не требуют запущенных внешних баз данных:
```bash
# Локальный запуск через виртуальное окружение:
pytest -v
```
