# Use an official Python runtime as a parent image
FROM python:3.9

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=run.py
ENV DEBUG=True

# Set the working directory
WORKDIR /app

# Accept the OpenAI API key as a build argument (optional if not needed during build)
ARG OPENAI_API_KEY
ENV OPENAI_API_KEY=${OPENAI_API_KEY}

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy environment sample and application code
COPY env.sample .env
COPY . .

# Copy the entrypoint script
COPY entrypoint.sh /entrypoint.sh

# Make the entrypoint script executable
RUN chmod +x /entrypoint.sh

# Unset the OPENAI_API_KEY to prevent it from being in the final image
ENV OPENAI_API_KEY=

# Use the entrypoint script
ENTRYPOINT ["/entrypoint.sh"]

# Gunicorn
CMD ["gunicorn", "--config", "gunicorn-cfg.py", "run:app"]
