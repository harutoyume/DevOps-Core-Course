# Use Python 3.13 slim image for smaller size while maintaining compatibility
FROM python:3.13-slim

# Create a non-root user for security best practices
# Using --system creates a system user without a home directory
# Using --group creates a group with the same name
RUN adduser --system --group --no-create-home appuser

# Set working directory
WORKDIR /app

# Copy requirements file first to leverage Docker layer caching
# If requirements.txt doesn't change, this layer will be cached
COPY requirements.txt .

# Install Python dependencies
# --no-cache-dir reduces image size by not storing pip cache
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
# This layer will only rebuild when application code changes
COPY app.py .

# Change ownership of application files to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Document that the application listens on port 5000
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]
