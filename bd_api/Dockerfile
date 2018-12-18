# Use an official Python runtime as a parent image
FROM python:3.7.1

# Copy the current directory contents into the container at /opt/app
COPY . /opt/app

# Set the working directory to /opt/app
WORKDIR /opt/app

# Define environment variable
ENV FLASK_ENV='development'
ENV FLASK_APP=bd_api

# Upgrade pip
RUN pip install --upgrade pip

# Install any needed packages specified in requirements.txt
RUN pip install --trusted-host pypi.python.org -r /opt/app/requirements.txt

RUN pip install -e &subdirectory=/opt/app//bd_api

# Run ra.py when the container launches
CMD ["python", "run.py"]
