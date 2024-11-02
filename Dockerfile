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

# Run the application
CMD ["python", "run.py"]
