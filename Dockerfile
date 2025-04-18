# Use the official Airflow image as the base image
FROM apache/airflow:2.8.1

# Set the working directory inside the container
WORKDIR /opt/airflow

# Copy the requirements file into the container
COPY requirements.txt /requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /requirements.txt

# Copy the project files into the container
COPY dags /opt/airflow/dags
COPY plugins /opt/airflow/plugins
COPY data /opt/airflow/data
COPY .env /opt/airflow/.env
COPY utils /opt/airflow/utils

# Set environment variables for Airflow
ENV AIRFLOW_HOME=/opt/airflow