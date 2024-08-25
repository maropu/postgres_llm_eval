FROM python:3.11-slim-bullseye
WORKDIR /workspace

# Install necessary packages
RUN apt-get update && apt-get install -y \
	vim \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Copy the minimum required stuff
COPY bin bin
COPY generated generated

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
