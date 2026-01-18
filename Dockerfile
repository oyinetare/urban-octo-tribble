# Use the official Python 3.13 slim image for a production-ready base
FROM python:3.13-slim

# Set the working directory inside the container
WORKDIR /app

# Set environment variables to optimize Python performance in Docker
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy and install dependencies first to leverage Docker layer caching
COPY pyproject.toml ./
RUN pip install --upgrade pip setuptools wheel && \
    pip install .

# Copy the rest of your application code
COPY . .

# Specify the command to run your application
CMD ["python", "main.py"]
