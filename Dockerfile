FROM python:3.11-slim

# Set metadata
LABEL maintainer="P2P Tracker"
LABEL description="Binance P2P Price Tracker"

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY price_tracker_prod.py .

# Create non-root user
RUN useradd -m -u 1000 tracker && \
    chown -R tracker:tracker /app && \
    mkdir -p /config && \
    chown -R tracker:tracker /config

# Switch to non-root user
USER tracker

# Health check - verify log file has been updated recently
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD test -f price_tracker.log && \
        test $(find price_tracker.log -mmin -5 2>/dev/null) || exit 1

# Run the tracker
CMD ["python", "price_tracker_prod.py", "--config", "/config/config.json"]
