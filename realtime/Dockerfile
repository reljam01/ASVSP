# Use the official Ubuntu image as a base
FROM ubuntu:20.04

# Set environment variables to avoid interactive prompts during package installations
ENV DEBIAN_FRONTEND=noninteractive

# Update the package list and install dependencies (librdkafka, build tools, etc.)
RUN apt-get update && apt-get install -y \
    build-essential \
    librdkafka-dev \
    gcc \
    make \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a working directory in the container
WORKDIR /usr/src/app

# Command to run the compiled C script (assumes data.csv is available in the container or mounted)
CMD ["./csv_to_kafka"]
