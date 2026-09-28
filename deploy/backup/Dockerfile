# pg_dump must match the server major version, so build on the same image.
FROM postgres:16-alpine
RUN apk add --no-cache python3 py3-boto3
COPY backup.py /backup.py
USER postgres
CMD ["python3", "-u", "/backup.py"]
