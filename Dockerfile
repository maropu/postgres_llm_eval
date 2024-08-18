FROM python:3.11-alpine
WORKDIR /workspace

# Install necessary packages
RUN apk add --no-cache \
    tree \
    vim

# Copy the minimum required stuff
COPY bin bin
COPY generated generated

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

