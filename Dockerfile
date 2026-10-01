FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y \
    gcc \
    libmariadb-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Train models if not already present
RUN python ml/train_churn_model.py && python ml/train_clv_model.py

# Expose Flask port
EXPOSE 5000

# Environment
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

CMD ["python", "app.py"]
