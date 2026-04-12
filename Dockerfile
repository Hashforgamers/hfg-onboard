# Dockerfile

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /code

# Install dependencies
COPY requirements.txt /code/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy project
COPY . /code/

# Create uploads directory
RUN mkdir -p /code/uploads/business_registration \
             /code/uploads/owner_identification_proof \
             /code/uploads/tax_identification_number \
             /code/uploads/bank_acc_details

# Expose port
EXPOSE 5052

# Run with production WSGI server
CMD ["sh", "-c", "exec gunicorn -w ${GUNICORN_WORKERS:-2} --threads ${GUNICORN_THREADS:-4} --timeout ${GUNICORN_TIMEOUT:-60} --graceful-timeout ${GUNICORN_GRACEFUL_TIMEOUT:-30} --keep-alive ${GUNICORN_KEEPALIVE:-5} --max-requests ${GUNICORN_MAX_REQUESTS:-1000} --max-requests-jitter ${GUNICORN_MAX_REQUESTS_JITTER:-100} -b 0.0.0.0:${PORT:-5052} wsgi:app"]
