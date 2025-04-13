FROM python:3.11.7

ENV PYTHONUNBUFFERED=1

WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app/
RUN pip install --no-cache-dir -r requirements.txt

COPY src /usr/src/app/src/
COPY alembic.ini /usr/src/app/
COPY migrations /usr/src/app/migrations

EXPOSE 8000

ENV PYTHONPATH=/usr/src/app/src
