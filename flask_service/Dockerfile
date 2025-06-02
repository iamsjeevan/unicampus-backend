# flask_service/Dockerfile 
# (Assumes build context is 'flask_service/')

FROM python:3.11-slim-bullseye
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV FLASK_APP run.py 
ENV FLASK_ENV production

WORKDIR /app 

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . . 

EXPOSE 8000
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:8000", "run:application"] 