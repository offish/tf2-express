FROM python:3.12-slim

ENV TZ=Europe/Oslo

RUN apt-get update && apt-get install -y tzdata && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.lock.txt .

RUN pip install --no-cache-dir -r requirements.lock.txt

COPY . .

CMD ["sleep", "infinity"]