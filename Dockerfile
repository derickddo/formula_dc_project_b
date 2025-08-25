FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app



# Copy the requirements file into the container
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . /app

EXPOSE 8080
