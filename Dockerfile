FROM python:3.11-slim
 
WORKDIR /app
 
# Install curl
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
 
# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
 
# Copy project files
COPY . .
 
# Make entrypoint executable
RUN chmod +x entrypoint.sh
 
EXPOSE 8501
 
CMD ["./entrypoint.sh"]
 