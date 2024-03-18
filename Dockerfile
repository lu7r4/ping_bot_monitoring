FROM python:3.11.5

WORKDIR /ping_bot_3.0

COPY requirements.txt .
RUN apt-get update && apt-get install -y nmap
RUN apt-get install -y traceroute
RUN apt-get install -y curl dnsutils
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "init_bot.py"]
