# Backup and Recovery Procedures

This document outlines backup and disaster recovery procedures for the Litecoin Knowledge Hub application.

## Backup Overview

### Data to Backup

1. **MongoDB Data:**
   - RAG knowledge base documents
   - User questions logs
   - CMS articles metadata
   - Data sources configuration

2. **Application Configuration:**
   - Environment variables (secrets stored separately)
   - Docker Compose configurations
   - Monitoring dashboards and alerts

3. **Vector Store:**
   - FAISS index (rebuilt from MongoDB, but backup recommended)

### Backup Frequency

- **MongoDB:** Daily automated backups
- **Configuration:** Version controlled (Git)
- **Vector Store:** Weekly (can be rebuilt from MongoDB)

## MongoDB Backup Procedures

### Automated Backups

#### Using MongoDB Tools (Recommended)

**Daily Backup Script:**

```bash
#!/bin/bash
# backup-mongodb.sh

BACKUP_DIR="/backups/mongodb"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Create backup directory
mkdir -p $BACKUP_DIR

# Perform backup
mongodump \
  --uri="$MONGO_URI" \
  --out="$BACKUP_DIR/$DATE" \
  --gzip

# Compress backup
tar -czf "$BACKUP_DIR/mongodb_backup_$DATE.tar.gz" "$BACKUP_DIR/$DATE"

# Remove uncompressed backup
rm -rf "$BACKUP_DIR/$DATE"

# Clean up old backups (retain for $RETENTION_DAYS days)
find $BACKUP_DIR -name "mongodb_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: mongodb_backup_$DATE.tar.gz"
```

**Scheduled via Cron:**

```bash
# Add to crontab (daily at 2 AM)
0 2 * * * /path/to/backup-mongodb.sh
```

#### Using Docker

**Backup Script for Docker:**

```bash
#!/bin/bash
# backup-mongodb-docker.sh

BACKUP_DIR="/backups/mongodb"
DATE=$(date +%Y%m%d_%H%M%S)
CONTAINER_NAME="litecoin-mongodb"
RETENTION_DAYS=30

mkdir -p $BACKUP_DIR

# Backup from Docker container
docker exec $CONTAINER_NAME mongodump \
  --out=/data/backup \
  --gzip

# Copy backup from container
docker cp $CONTAINER_NAME:/data/backup $BACKUP_DIR/$DATE

# Compress backup
tar -czf "$BACKUP_DIR/mongodb_backup_$DATE.tar.gz" "$BACKUP_DIR/$DATE"

# Clean up
rm -rf "$BACKUP_DIR/$DATE"
docker exec $CONTAINER_NAME rm -rf /data/backup

# Clean up old backups
find $BACKUP_DIR -name "mongodb_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: mongodb_backup_$DATE.tar.gz"
```

### Manual Backup

**One-time Backup:**

```bash
# From host
docker exec litecoin-mongodb mongodump --out=/data/backup --gzip
docker cp litecoin-mongodb:/data/backup ./mongodb_backup_$(date +%Y%m%d)

# Or using mongodump directly (if MongoDB client installed)
mongodump --uri="mongodb://localhost:27017" --out=./mongodb_backup --gzip
```

### Backup Storage

**Recommended Locations:**

1. **Local Storage:**
   - `/backups/mongodb` (on backup server)
   - Minimum 30 days retention

2. **Cloud Storage:**
   - AWS S3 with versioning
   - Google Cloud Storage
   - Azure Blob Storage

3. **Offsite Backup:**
   - Weekly offsite backups
   - Different geographic region
   - Encrypted backups

**Encryption:**

```bash
# Encrypt backup before storing
gpg --encrypt --recipient backup@example.com mongodb_backup.tar.gz
```

## Recovery Procedures

### MongoDB Restore

#### From Backup File

**Using mongorestore:**

```bash
# Extract backup
tar -xzf mongodb_backup_YYYYMMDD.tar.gz

# Restore to MongoDB
mongorestore \
  --uri="$MONGO_URI" \
  --drop \
  --gzip \
  ./mongodb_backup_YYYYMMDD
```

**Using Docker:**

```bash
# Copy backup to container
docker cp mongodb_backup_YYYYMMDD litecoin-mongodb:/data/backup

# Restore
docker exec litecoin-mongodb mongorestore \
  --drop \
  --gzip \
  /data/backup
```

#### Point-in-Time Recovery

MongoDB point-in-time recovery requires:

1. **Oplog enabled:** Ensure MongoDB oplog is enabled
2. **Regular backups:** Daily backups available
3. **Oplog backups:** Continuous oplog backups

**Restore to Specific Time:**

```bash
# Restore from backup
mongorestore --uri="$MONGO_URI" --drop mongodb_backup_YYYYMMDD

# Apply oplog to specific time
mongorestore --uri="$MONGO_URI" --oplogReplay --oplogLimit <timestamp> oplog_backup
```

### Partial Restore

**Restore Specific Database:**

```bash
mongorestore \
  --uri="$MONGO_URI" \
  --db=litecoin_rag_db \
  --drop \
  ./mongodb_backup_YYYYMMDD/litecoin_rag_db
```

**Restore Specific Collection:**

```bash
mongorestore \
  --uri="$MONGO_URI" \
  --db=litecoin_rag_db \
  --collection=litecoin_docs \
  --drop \
  ./mongodb_backup_YYYYMMDD/litecoin_rag_db/litecoin_docs.bson.gz
```

### Application Recovery

#### Full Application Restore

1. **Restore MongoDB:**
   ```bash
   ./restore-mongodb.sh mongodb_backup_YYYYMMDD.tar.gz
   ```

2. **Rebuild Vector Store:**
   ```bash
   docker exec litecoin-backend python backend/utils/rebuild_vector_store.py
   ```

3. **Restart Services:**
   ```bash
   docker-compose -f docker-compose.prod.yml restart
   ```

4. **Verify Recovery:**
   - Check health endpoints
   - Verify data integrity
   - Test API functionality

#### Vector Store Recovery

**Rebuild from MongoDB:**

```bash
# Rebuild vector store from MongoDB
docker exec litecoin-backend python backend/utils/rebuild_vector_store.py

# Or trigger via API
curl -X POST http://localhost:8000/api/v1/sources/{source_id}/refresh
```

## Disaster Recovery Plan

### Recovery Time Objectives (RTO)

- **Critical Systems:** 4 hours
- **Full Application:** 24 hours
- **Data Recovery:** 1 hour

### Recovery Point Objectives (RPO)

- **MongoDB Data:** 24 hours (daily backups)
- **Configuration:** Near real-time (Git)
- **Vector Store:** 24 hours (rebuildable from MongoDB)

### Disaster Scenarios

#### Scenario 1: Database Corruption

**Symptoms:**
- MongoDB errors on query
- Data inconsistencies
- Application errors

**Recovery:**
1. Stop application
2. Identify last known good backup
3. Restore from backup
4. Verify data integrity
5. Rebuild vector store
6. Restart services

**Estimated Time:** 2-4 hours

#### Scenario 2: Complete Data Loss

**Symptoms:**
- Empty database
- All data missing
- Service unavailable

**Recovery:**
1. Restore from most recent backup
2. Rebuild vector store
3. Verify all services
4. Test functionality

**Estimated Time:** 4-6 hours

#### Scenario 3: Server Failure

**Symptoms:**
- Server unavailable
- Services down
- Cannot connect

**Recovery:**
1. Provision new server
2. Restore from backup
3. Restore application configuration
4. Restore MongoDB data
5. Rebuild vector store
6. Restart services

**Estimated Time:** 6-12 hours

#### Scenario 4: Ransomware/Attack

**Symptoms:**
- Data encrypted
- Unauthorized access
- System compromise

**Recovery:**
1. Isolate affected systems
2. Assess damage
3. Restore from clean backup
4. Patch vulnerabilities
5. Strengthen security
6. Resume operations

**Estimated Time:** 12-24 hours

## Backup Verification

### Automated Verification

**Backup Integrity Check:**

```bash
#!/bin/bash
# verify-backup.sh

BACKUP_FILE=$1

# Extract and verify
tar -tzf $BACKUP_FILE > /dev/null
if [ $? -eq 0 ]; then
    echo "Backup archive is valid"
else
    echo "Backup archive is corrupted!"
    exit 1
fi

# Verify MongoDB backup structure
tar -xzf $BACKUP_FILE -C /tmp/verify
if [ -d "/tmp/verify/YYYYMMDD" ]; then
    echo "Backup structure is valid"
else
    echo "Backup structure is invalid!"
    exit 1
fi
```

### Manual Verification

**Monthly Backup Restore Test:**

1. Restore backup to test environment
2. Verify data integrity
3. Test application functionality
4. Document test results

## Backup Retention

### Retention Policy

- **Daily Backups:** 30 days
- **Weekly Backups:** 12 weeks
- **Monthly Backups:** 12 months
- **Yearly Backups:** 7 years

### Backup Rotation

```bash
# Keep daily backups for 30 days
find /backups/mongodb -name "mongodb_backup_*.tar.gz" -mtime +30 -delete

# Archive weekly backups
find /backups/mongodb -name "mongodb_backup_*.tar.gz" -mtime +7 -exec mv {} /backups/archive/weekly/ \;

# Archive monthly backups
find /backups/archive/weekly -name "mongodb_backup_*.tar.gz" -mtime +84 -exec mv {} /backups/archive/monthly/ \;
```

## Backup Monitoring

### Health Checks

- **Backup Success:** Verify backup completes successfully
- **Backup Size:** Monitor backup size for anomalies
- **Backup Age:** Alert if backup is older than 24 hours
- **Disk Space:** Monitor backup storage disk space

### Alerting

Set up alerts for:
- Backup failures
- Backup age > 24 hours
- Disk space < 20%
- Backup verification failures

## Best Practices

1. **Automate Backups:**
   - Use cron jobs or scheduled tasks
   - Automate verification
   - Set up monitoring

2. **Test Restores:**
   - Test restores regularly
   - Document restore procedures
   - Verify backup integrity

3. **Offsite Backups:**
   - Store backups offsite
   - Use cloud storage
   - Encrypt backups

4. **Documentation:**
   - Document all procedures
   - Keep runbooks updated
   - Train team on recovery

5. **Regular Reviews:**
   - Review backup procedures quarterly
   - Update retention policies
   - Improve disaster recovery plan

## Additional Resources

- [MongoDB Backup Documentation](https://docs.mongodb.com/manual/backup/)
- [Disaster Recovery Planning](https://docs.mongodb.com/manual/core/backups/)
- [Security Hardening Guide](./SECURITY_HARDENING.md)

