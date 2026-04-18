FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source files
COPY . .

# Expose the port FastAPI runs on
EXPOSE 8000

# Start the server
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
