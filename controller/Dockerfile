FROM python:3.11-slim

WORKDIR /app

RUN pip install -U pip

COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

COPY app /app/app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
