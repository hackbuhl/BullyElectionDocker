FROM python:3.8-slim-buster
WORKDIR /app
RUN pip3 install zerorpc gevent colored
COPY . .

CMD [ "python3","mainscript.py", "172.17.0.3:9001"]