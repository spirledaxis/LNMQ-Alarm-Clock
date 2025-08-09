FROM python:3.13

WORKDIR /app

ENV TZ="America/Los_Angeles"
ENV PYTHONUNBUFFERED=1

COPY requirements.txt /app

RUN pip install --trusted-host pypi.python.org -r requirements.txt

COPY . /app
CMD ["python3.13", "-u", "lights.py"]