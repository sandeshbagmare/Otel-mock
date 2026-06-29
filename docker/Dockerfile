# All-in-one image: runs every mock provider + the unified dashboard.
# Pure stdlib, so the image is tiny and needs no pip install.
FROM python:3.12-slim

WORKDIR /app
COPY mockotel ./mockotel
COPY providers.json ./providers.json
COPY examples ./examples

# 5001-5008 = providers, 8080 = unified dashboard
EXPOSE 5001 5002 5003 5004 5005 5006 5007 5008 8080

ENTRYPOINT ["python", "-m", "mockotel"]
CMD ["--all", "--host", "0.0.0.0", "--no-browser"]
