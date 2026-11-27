FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements-web.txt ./
RUN pip install --no-cache-dir -r requirements-web.txt && useradd --create-home app
# Explicitly exclude the local database module and its development credentials.
COPY part1/__init__.py part1/integrity.py ./part1/
COPY part2/__init__.py part2/operations.py ./part2/
COPY part3/ ./part3/
COPY sql/schema.sql sql/seed.sql sql/accepted_paper_schedule.sql ./sql/
USER app
EXPOSE 10000
CMD ["python", "-m", "part3.serve"]
