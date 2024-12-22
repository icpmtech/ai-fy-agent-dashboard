# Use an official Python runtime as a parent image
FROM python:3.9

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=run.py
ENV DEBUG=True

# Accept the OpenAI API key as a build argument
ARG OPENAI_API_KEY

# Set the environment variable for use during build
ENV OPENAI_API_KEY=${OPENAI_API_KEY}

# Set the working directory
WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy environment sample and application code
COPY env.sample .env
COPY . .

# Initialize the database with the API key available
RUN flask db init
RUN flask db migrate
RUN flask db upgrade

# Unset the OPENAI_API_KEY to prevent it from being in the final image
ENV OPENAI_API_KEY=

# Command to run the application using Gunicorn
CMD ["gunicorn", "--config", "gunicorn-cfg.py", "run:app"]
