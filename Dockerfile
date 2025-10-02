# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the dependency file to the working directory
COPY ./requirements.txt /app/requirements.txt

# Install any needed packages specified in requirements.txt
# --no-cache-dir: Disables the pip cache, which reduces the image size.
# --trusted-host: Required if you're behind a proxy, but good practice.
RUN pip install --no-cache-dir --trusted-host pypi.python.org -r requirements.txt

# Copy the rest of your application's code to the working directory
COPY . /app

# Expose the port the app runs on
EXPOSE 8000