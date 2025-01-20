FROM python:3.11.7

ENV PYTHONUNBUFFERED=1

WORKDIR /usr/src/app

COPY . /usr/src/app/

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

ENV PYTHONPATH=/usr/src/app/src

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
