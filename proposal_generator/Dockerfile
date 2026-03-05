FROM python:3.11-slim

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user for security and to satisfy HF Spaces permissions
RUN useradd -m -u 1000 user
USER user

# Ensure output and data directories exist with proper permissions
ENV HOME=/home/user \
	PATH=/home/user/.local/bin:$PATH
RUN mkdir -p /home/user/app/outputs /home/user/app/data

WORKDIR /home/user/app
COPY --chown=user . .

# Start FastAPI/Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
