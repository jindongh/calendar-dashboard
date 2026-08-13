FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV TZ=America/Los_Angeles

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libnss3 \
       avahi-daemon \
       avahi-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY cast_dashboard.py .
COPY start.py .

COPY templates ./templates
COPY static ./static

EXPOSE 8080

CMD ["python", "start.py"]
