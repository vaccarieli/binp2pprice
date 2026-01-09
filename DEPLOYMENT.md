# Production Deployment Guide

## Pre-Deployment Checklist

- [ ] Python 3.8+ installed
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Config file created from `config.example.json`
- [ ] Config file permissions secured (`chmod 600 config.json` on Linux)
- [ ] Email/webhook credentials configured
- [ ] Test run completed successfully
- [ ] Log directory exists and is writable
- [ ] Firewall rules configured (if needed for SMTP)

## Linux Deployment (systemd)

### Step 1: Create User and Directory

```bash
# Create dedicated user (no login)
sudo useradd -r -s /bin/false tracker

# Create installation directory
sudo mkdir -p /opt/p2p_tracker
sudo chown tracker:tracker /opt/p2p_tracker

# Copy files
sudo cp price_tracker_prod.py /opt/p2p_tracker/
sudo cp config.json /opt/p2p_tracker/
sudo chown tracker:tracker /opt/p2p_tracker/*
sudo chmod 600 /opt/p2p_tracker/config.json
```

### Step 2: Install Dependencies

```bash
# Using system Python
sudo pip3 install -r requirements.txt

# OR using virtual environment (recommended)
cd /opt/p2p_tracker
sudo -u tracker python3 -m venv venv
sudo -u tracker venv/bin/pip install -r requirements.txt
```

If using venv, update service file ExecStart:
```
ExecStart=/opt/p2p_tracker/venv/bin/python /opt/p2p_tracker/price_tracker_prod.py --config /opt/p2p_tracker/config.json
```

### Step 3: Install and Start Service

```bash
# Copy service file
sudo cp p2p-tracker.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable p2p-tracker

# Start service
sudo systemctl start p2p-tracker

# Check status
sudo systemctl status p2p-tracker
```

### Step 4: Monitor Logs

```bash
# View real-time logs
sudo journalctl -u p2p-tracker -f

# View last 100 lines
sudo journalctl -u p2p-tracker -n 100

# View today's logs
sudo journalctl -u p2p-tracker --since today

# Check application log file
sudo tail -f /opt/p2p_tracker/price_tracker.log
```

### Step 5: Manage Service

```bash
# Stop service
sudo systemctl stop p2p-tracker

# Restart service
sudo systemctl restart p2p-tracker

# Disable service (don't start on boot)
sudo systemctl disable p2p-tracker

# View service configuration
sudo systemctl cat p2p-tracker
```

## Windows Deployment

### Option 1: Task Scheduler (Recommended)

1. Open Task Scheduler (taskschd.msc)
2. Create New Task (not Basic Task)

**General Tab:**
- Name: `Binance P2P Tracker`
- Description: `Monitors P2P prices and sends alerts`
- Run whether user is logged on or not
- Run with highest privileges
- Configure for: Windows 10

**Triggers Tab:**
- New Trigger
- Begin the task: At startup
- Delay task for: 30 seconds
- Enabled: ✓

**Actions Tab:**
- New Action
- Action: Start a program
- Program/script: `C:\Python39\python.exe`
- Arguments: `price_tracker_prod.py --config config.json`
- Start in: `C:\Users\YourUser\p2p_tracker`

**Conditions Tab:**
- Uncheck: Start only if computer is on AC power
- Check: Wake computer to run this task

**Settings Tab:**
- Allow task to be run on demand: ✓
- Run task as soon as possible after scheduled start is missed: ✓
- If task fails, restart every: 5 minutes
- Attempt to restart up to: 3 times
- If running task does not end when requested: Stop the existing instance

**Save and Test:**
- Right-click task → Run
- Check logs in `price_tracker.log`

### Option 2: NSSM (Non-Sucking Service Manager)

```powershell
# Download NSSM from https://nssm.cc/download
# Extract and run as administrator

# Install service
nssm install P2PTracker "C:\Python39\python.exe"
nssm set P2PTracker AppDirectory "C:\Users\YourUser\p2p_tracker"
nssm set P2PTracker AppParameters "price_tracker_prod.py --config config.json"
nssm set P2PTracker DisplayName "Binance P2P Price Tracker"
nssm set P2PTracker Description "Monitors P2P cryptocurrency prices"
nssm set P2PTracker Start SERVICE_AUTO_START

# Start service
nssm start P2PTracker

# Check status
nssm status P2PTracker

# View logs
type price_tracker.log

# Stop service
nssm stop P2PTracker

# Remove service
nssm remove P2PTracker confirm
```

### Option 3: PowerShell Script with Auto-Restart

Save as `start_tracker.ps1`:

```powershell
# Binance P2P Tracker Launcher with Auto-Restart
$scriptPath = "C:\Users\YourUser\p2p_tracker"
$pythonExe = "python"
$trackerScript = "price_tracker_prod.py"

Set-Location $scriptPath

while ($true) {
    Write-Host "Starting P2P Tracker at $(Get-Date)"

    $process = Start-Process -FilePath $pythonExe `
        -ArgumentList "$trackerScript --config config.json" `
        -NoNewWindow `
        -PassThru `
        -RedirectStandardOutput "tracker_stdout.log" `
        -RedirectStandardError "tracker_stderr.log"

    # Wait for process to exit
    $process.WaitForExit()

    Write-Host "Tracker stopped with exit code $($process.ExitCode)"
    Write-Host "Restarting in 10 seconds..."
    Start-Sleep -Seconds 10
}
```

Run in background:
```powershell
powershell -WindowStyle Hidden -File start_tracker.ps1
```

## Docker Deployment

### Step 1: Create Dockerfile

```dockerfile
FROM python:3.11-slim

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY price_tracker_prod.py .

# Create non-root user
RUN useradd -m -u 1000 tracker && \
    chown -R tracker:tracker /app
USER tracker

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD test -f price_tracker.log && test $(find price_tracker.log -mmin -5) || exit 1

# Run tracker
CMD ["python", "price_tracker_prod.py", "--config", "/config/config.json"]
```

### Step 2: Create docker-compose.yml

```yaml
version: '3.8'

services:
  p2p-tracker:
    build: .
    container_name: p2p_tracker
    restart: unless-stopped
    volumes:
      - ./config.json:/config/config.json:ro
      - ./logs:/app:rw
    environment:
      - TZ=America/Caracas
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M
        reservations:
          cpus: '0.1'
          memory: 64M
```

### Step 3: Build and Run

```bash
# Build image
docker-compose build

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down

# Restart
docker-compose restart
```

## Cloud Deployment (VPS)

### Recommended Providers
- **DigitalOcean**: $6/month droplet
- **AWS EC2**: t3.micro (free tier eligible)
- **Linode**: $5/month Nanode
- **Vultr**: $3.50/month instance

### Minimum Requirements
- CPU: 1 core
- RAM: 512 MB
- Storage: 10 GB
- Network: 500 GB transfer

### Setup Steps

1. **Create VPS Instance**
   - Ubuntu 22.04 LTS or Debian 12
   - Add SSH key
   - Enable firewall

2. **Initial Server Setup**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install -y python3 python3-pip python3-venv

# Create user
sudo useradd -r -m -s /bin/bash tracker
sudo su - tracker
```

3. **Deploy Application**
```bash
# Clone or upload files
cd ~
mkdir p2p_tracker
cd p2p_tracker

# Create venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Copy config
cp config.example.json config.json
nano config.json  # Edit configuration
chmod 600 config.json
```

4. **Configure Systemd Service**
```bash
# Exit tracker user
exit

# Copy service file
sudo cp p2p-tracker.service /etc/systemd/system/

# Edit service paths if needed
sudo nano /etc/systemd/system/p2p-tracker.service

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable p2p-tracker
sudo systemctl start p2p-tracker
```

5. **Configure Firewall**
```bash
# Only needed if using custom monitoring endpoint
sudo ufw allow 22/tcp
sudo ufw enable
```

## Monitoring and Maintenance

### Log Rotation

Create `/etc/logrotate.d/p2p-tracker`:

```
/opt/p2p_tracker/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 tracker tracker
    sharedscripts
    postrotate
        systemctl reload p2p-tracker > /dev/null 2>&1 || true
    endscript
}
```

### Health Monitoring Script

Save as `check_health.sh`:

```bash
#!/bin/bash

LOG_FILE="/opt/p2p_tracker/price_tracker.log"
MAX_AGE_MINUTES=10

if [ ! -f "$LOG_FILE" ]; then
    echo "ERROR: Log file not found"
    exit 1
fi

# Check if log file has been updated recently
LAST_MODIFIED=$(stat -c %Y "$LOG_FILE")
CURRENT_TIME=$(date +%s)
AGE_MINUTES=$(( ($CURRENT_TIME - $LAST_MODIFIED) / 60 ))

if [ $AGE_MINUTES -gt $MAX_AGE_MINUTES ]; then
    echo "ERROR: Tracker appears stuck (log not updated for $AGE_MINUTES minutes)"
    systemctl restart p2p-tracker
    exit 1
fi

echo "OK: Tracker is healthy"
exit 0
```

Add to crontab:
```bash
*/5 * * * * /opt/p2p_tracker/check_health.sh
```

### Backup Configuration

```bash
# Backup script
#!/bin/bash
BACKUP_DIR="/opt/backups"
mkdir -p "$BACKUP_DIR"

tar -czf "$BACKUP_DIR/p2p_tracker_$(date +%Y%m%d_%H%M%S).tar.gz" \
    /opt/p2p_tracker/config.json \
    /opt/p2p_tracker/price_history_*.json

# Keep only last 7 backups
ls -t "$BACKUP_DIR"/p2p_tracker_*.tar.gz | tail -n +8 | xargs rm -f
```

## Troubleshooting

### Service Won't Start

```bash
# Check service status
sudo systemctl status p2p-tracker

# Check logs
sudo journalctl -u p2p-tracker -n 50

# Test configuration
sudo -u tracker python3 /opt/p2p_tracker/price_tracker_prod.py --config /opt/p2p_tracker/config.json
```

### High CPU/Memory Usage

```bash
# Check resource usage
sudo systemctl status p2p-tracker

# Adjust service limits in p2p-tracker.service
sudo systemctl edit p2p-tracker
```

Add:
```ini
[Service]
MemoryLimit=128M
CPUQuota=25%
```

### Rate Limiting Issues

- Increase `check_interval` in config.json to 60+ seconds
- Check Binance status: https://www.binance.com/en/support/announcement

### Email Alerts Not Working

```bash
# Test SMTP connection
telnet smtp.gmail.com 587

# Check firewall
sudo ufw status

# Verify credentials in config.json
```

## Security Best Practices

1. **File Permissions**
   ```bash
   chmod 600 config.json
   chmod 640 *.log
   chmod 750 price_tracker_prod.py
   ```

2. **Dedicated User**
   - Run as non-root user
   - No shell access needed
   - Limited file system access

3. **Network Security**
   - Use HTTPS for webhooks
   - Use TLS for email (port 587/465)
   - Don't expose unnecessary ports

4. **Credential Management**
   - Use app passwords (not main passwords)
   - Consider environment variables
   - Never commit config.json to git

5. **Updates**
   ```bash
   # Update dependencies monthly
   pip list --outdated
   pip install -U requests urllib3
   ```

## Performance Tuning

- **Interval**: 30-60 seconds optimal
- **History**: Keep 24 hours (default)
- **Log Level**: INFO for production, DEBUG for troubleshooting
- **Max Retries**: 3 recommended

## Support

For issues, check:
1. Application logs
2. System logs (journalctl)
3. Network connectivity
4. Binance P2P status
5. Email/webhook configuration
