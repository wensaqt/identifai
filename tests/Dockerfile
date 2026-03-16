FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY tests/requirements.txt requirements-test.txt
COPY dataset/requirements.txt dataset-requirements.txt
RUN pip install --no-cache-dir -r requirements-test.txt -r dataset-requirements.txt

COPY . .

CMD ["python", "-m", "pytest", "tests/", "-v"]
