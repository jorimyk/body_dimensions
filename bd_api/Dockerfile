# Use an official Python runtime as a parent image
FROM python:3.6.3

# Copy the current directory contents into the container at /opt/app
COPY . /opt/app

# Set the working directory to /opt/app
WORKDIR /opt/app

# Define environment variable
ENV FLASK_DEBUG=1
ENV FLASK_APP=bd_api

# Install any needed packages specified in requirements.txt
RUN pip install --trusted-host pypi.python.org -r /opt/app/requirements.txt

RUN pip install -e &subdirectory=/opt/app//bd_api

# Run ra.py when the container launches
CMD ["python", "run.py"]
