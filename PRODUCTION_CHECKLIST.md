# Production Readiness Checklist

Use this checklist to ensure your P2P price tracker is production-ready.

## Pre-Deployment

### Environment Setup
- [ ] Python 3.8+ installed and verified (`python --version`)
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Git repository initialized (optional but recommended)
- [ ] `.gitignore` file present and protecting sensitive files
- [ ] Virtual environment created and activated (recommended)

### Configuration
- [ ] `config.json` created from `config.example.json`
- [ ] Payment methods configured correctly
- [ ] Check interval set (minimum 30 seconds recommended)
- [ ] Alert threshold configured (2.0% default is reasonable)
- [ ] Asset and fiat currency verified (USDT/VES default)

### Security
- [ ] Config file permissions secured (`chmod 600 config.json` on Linux)
- [ ] No secrets committed to git
- [ ] Using app passwords (not main passwords) for email
- [ ] Config file NOT named `config.example.json` (use `config.json`)
- [ ] Sensitive data not in environment variables visible to other users

### Email Alerts (if enabled)
- [ ] SMTP host configured correctly
- [ ] SMTP port configured (587 for TLS, 465 for SSL)
- [ ] From email address valid and accessible
- [ ] To email address valid
- [ ] App password generated and configured (for Gmail)
- [ ] Test email sent successfully
- [ ] Firewall allows outbound connections on SMTP port

### Webhook Alerts (if enabled)
- [ ] Webhook URL valid and accessible
- [ ] Webhook service configured to receive alerts
- [ ] Test webhook sent successfully
- [ ] HTTPS used (not HTTP)

### Testing
- [ ] Script runs without errors (`python price_tracker_prod.py --help`)
- [ ] Test run completed successfully (at least 20 minutes)
- [ ] Logs being written to file correctly
- [ ] Price history being saved (`price_history_*.json` created)
- [ ] Console output displays correctly
- [ ] Alerts triggered correctly when threshold exceeded
- [ ] Rate limiting handled gracefully (if tested)
- [ ] Graceful shutdown works (`Ctrl+C`)

## Deployment

### Linux (systemd)
- [ ] Service file created (`p2p-tracker.service`)
- [ ] Dedicated user created (`tracker`)
- [ ] Installation directory created (`/opt/p2p_tracker`)
- [ ] Files copied to installation directory
- [ ] File ownership and permissions correct
- [ ] Service file copied to `/etc/systemd/system/`
- [ ] Service enabled (`systemctl enable p2p-tracker`)
- [ ] Service started (`systemctl start p2p-tracker`)
- [ ] Service status verified (`systemctl status p2p-tracker`)
- [ ] Logs accessible via journalctl
- [ ] Service survives reboot

### Windows (Task Scheduler)
- [ ] Task created in Task Scheduler
- [ ] Task configured to run at startup
- [ ] Task configured to restart on failure
- [ ] Task runs with correct user permissions
- [ ] Task working directory set correctly
- [ ] Task tested manually (Right-click → Run)
- [ ] Logs being written correctly
- [ ] Task survives reboot

### Docker
- [ ] Dockerfile created
- [ ] docker-compose.yml configured
- [ ] Image builds successfully (`docker-compose build`)
- [ ] Container starts successfully (`docker-compose up -d`)
- [ ] Logs accessible (`docker-compose logs -f`)
- [ ] Config mounted correctly as read-only volume
- [ ] Logs directory mounted with write permissions
- [ ] Health check passing
- [ ] Container restarts automatically on failure
- [ ] Resource limits configured

## Monitoring

### Logging
- [ ] Log file being created and updated
- [ ] Log rotation configured (optional but recommended)
- [ ] Log level appropriate (INFO for production)
- [ ] Errors being logged with stack traces
- [ ] Alerts being logged with details
- [ ] Log file size manageable

### Health Checks
- [ ] Script running continuously
- [ ] No repeated errors in logs
- [ ] Price history growing over time
- [ ] Consecutive failures count stays at 0
- [ ] Health check script created (optional)
- [ ] Health check scheduled in cron/Task Scheduler (optional)

### Performance
- [ ] CPU usage reasonable (<5%)
- [ ] Memory usage reasonable (<100MB)
- [ ] Disk space sufficient for logs and history
- [ ] Network bandwidth sufficient (~1KB per check)
- [ ] No rate limiting errors in production

## Maintenance

### Backup
- [ ] Config file backed up
- [ ] Backup script created (optional)
- [ ] Backup schedule configured (optional)
- [ ] Restore procedure tested (optional)

### Updates
- [ ] Update procedure documented
- [ ] Dependencies checked for security updates
- [ ] Testing environment available for updates
- [ ] Rollback plan in place

### Documentation
- [ ] README.md reviewed and understood
- [ ] QUICK_START.md followed successfully
- [ ] DEPLOYMENT.md reviewed for deployment type
- [ ] Contact information documented for support
- [ ] Runbook created for common operations (optional)

## Post-Deployment

### Validation (First 24 Hours)
- [ ] Service running continuously
- [ ] No unexpected restarts
- [ ] Alerts triggered appropriately
- [ ] Email/webhook notifications received
- [ ] Log file growing normally
- [ ] No rate limiting issues
- [ ] CPU and memory usage stable

### Week 1 Review
- [ ] Check logs for any errors or warnings
- [ ] Verify alert threshold is appropriate
- [ ] Review alert frequency (too many/too few?)
- [ ] Confirm check interval is optimal
- [ ] Validate email/webhook notifications working
- [ ] Review resource usage trends

### Monthly Maintenance
- [ ] Review and rotate logs
- [ ] Check for security updates
- [ ] Update dependencies if needed
- [ ] Review and clean up old history files
- [ ] Verify backup integrity (if configured)
- [ ] Check disk space usage

## Troubleshooting Resources

- [ ] Application logs: `price_tracker.log`
- [ ] System logs: `journalctl -u p2p-tracker` (Linux)
- [ ] Price history: `price_history_VES_USDT.json`
- [ ] Configuration: `config.json`
- [ ] Documentation: `README.md`, `DEPLOYMENT.md`, `QUICK_START.md`

## Security Review

### Access Control
- [ ] Application runs as non-root user (Linux)
- [ ] Config file readable only by application user
- [ ] Log files have appropriate permissions
- [ ] No unnecessary network ports exposed
- [ ] Firewall configured correctly

### Credential Management
- [ ] No plaintext passwords in logs
- [ ] App passwords used instead of main passwords
- [ ] Credentials not shared inappropriately
- [ ] Regular password rotation scheduled (if applicable)

### Network Security
- [ ] HTTPS used for webhooks
- [ ] TLS used for email (port 587/465)
- [ ] No sensitive data in URL parameters
- [ ] API endpoints accessed over HTTPS only

### Code Security
- [ ] Input validation enabled (added in production version)
- [ ] Path traversal protection active
- [ ] URL validation for webhooks
- [ ] Email validation for alerts
- [ ] Rate limiting respected

## Compliance (If Applicable)

- [ ] Data retention policy defined
- [ ] Privacy policy reviewed
- [ ] Terms of service acknowledged
- [ ] Logging complies with regulations
- [ ] Data handling procedures documented

## Sign-Off

**Date:** _________________

**Deployed By:** _________________

**Environment:** _________________

**Configuration:**
- Check Interval: _______s
- Alert Threshold: _______%
- Payment Methods: _________________
- Email Enabled: Yes / No
- Webhook Enabled: Yes / No

**Notes:**
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________

**Production Approval:** _________________

---

## Quick Reference

### Start Service
```bash
# Linux
sudo systemctl start p2p-tracker

# Windows
# Task Scheduler → Right-click task → Run

# Docker
docker-compose up -d
```

### Stop Service
```bash
# Linux
sudo systemctl stop p2p-tracker

# Windows
# Task Scheduler → Right-click task → End

# Docker
docker-compose down
```

### View Logs
```bash
# Linux (journalctl)
sudo journalctl -u p2p-tracker -f

# Application log
tail -f price_tracker.log

# Docker
docker-compose logs -f
```

### Restart Service
```bash
# Linux
sudo systemctl restart p2p-tracker

# Windows
# Stop and start task in Task Scheduler

# Docker
docker-compose restart
```
