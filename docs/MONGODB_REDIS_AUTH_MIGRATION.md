# MongoDB and Redis Authentication Migration Guide

> **Status:** ✅ Implementation Complete  
> **Priority:** 🚨 **PUBLIC LAUNCH BLOCKER** (CRIT-3, CRIT-4)  
> **Estimated Time:** 1-2 hours

This guide walks you through enabling authentication for MongoDB and Redis in your existing deployment **without losing any data**.

## Overview

With the repository now public, unauthenticated MongoDB and Redis instances pose a critical security risk. Anyone can `docker-compose up` on a $5 VPS and instantly have unauthenticated databases exposed to the internet.

This migration enables authentication while preserving all existing Payload CMS data and other database contents.

## Prerequisites

- Existing MongoDB container with data (you want to keep)
- Docker Compose setup
- Access to running containers

## Step-by-Step Migration

### Step 1: Generate Secure Passwords

Generate strong, random passwords for all services:

```bash
# Generate passwords
MONGO_ROOT_PASSWORD=$(openssl rand -base64 32)
MONGO_APP_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 32)

# Save them securely (you'll need these!)
echo "MONGO_ROOT_PASSWORD=$MONGO_ROOT_PASSWORD"
echo "MONGO_APP_PASSWORD=$MONGO_APP_PASSWORD"
echo "REDIS_PASSWORD=$REDIS_PASSWORD"
```

**⚠️ IMPORTANT:** Save these passwords securely. You'll need them for the next steps and to update your environment files.

### Step 2: Create MongoDB Users (While Still Unauthenticated)

**This step must be done BEFORE enabling authentication.** Once `--auth` is enabled, you won't be able to create users without credentials.

#### Option A: Using the Provided Script (Recommended)

1. Ensure your MongoDB container is running:
   ```bash
   docker ps | grep mongodb
   ```

2. Run the user creation script:
   ```bash
   docker exec -i \
     -e MONGO_ROOT_USERNAME=admin \
     -e MONGO_ROOT_PASSWORD="YOUR_MONGO_ROOT_PASSWORD_HERE" \
     -e MONGO_APP_USERNAME=litecoin_app \
     -e MONGO_APP_PASSWORD="YOUR_MONGO_APP_PASSWORD_HERE" \
     litecoin-mongodb mongosh < scripts/create-mongo-users.js
   ```

   Replace `YOUR_MONGO_ROOT_PASSWORD_HERE` and `YOUR_MONGO_APP_PASSWORD_HERE` with the passwords you generated in Step 1.

#### Option B: Manual Creation via mongosh

1. Connect to MongoDB:
   ```bash
   docker exec -it litecoin-mongodb mongosh
   ```

2. Create root admin user:
   ```javascript
   use admin
   db.createUser({
     user: "admin",
     pwd: "YOUR_MONGO_ROOT_PASSWORD_HERE",
     roles: [{ role: "root", db: "admin" }]
   })
   ```

3. Create application user for litecoin_rag_db:
   ```javascript
   use litecoin_rag_db
   db.createUser({
     user: "litecoin_app",
     pwd: "YOUR_MONGO_APP_PASSWORD_HERE",
     roles: [
       { role: "readWrite", db: "litecoin_rag_db" },
       { role: "readWrite", db: "payload_cms" }
     ]
   })
   ```

4. Create application user for payload_cms:
   ```javascript
   use payload_cms
   db.createUser({
     user: "litecoin_app",
     pwd: "YOUR_MONGO_APP_PASSWORD_HERE",
     roles: [{ role: "readWrite", db: "payload_cms" }]
   })
   ```

5. Verify users were created:
   ```javascript
   use admin
   db.getUsers()
   ```

6. Exit mongosh:
   ```javascript
   exit
   ```

### Step 3: Update Environment Files

Update your environment files (`.env.docker.prod`, `.env.docker.dev`, or `.env.prod-local`) with the passwords and updated connection strings:

```bash
# MongoDB Authentication
MONGO_ROOT_USERNAME=admin
MONGO_ROOT_PASSWORD=YOUR_MONGO_ROOT_PASSWORD_HERE
MONGO_APP_USERNAME=litecoin_app
MONGO_APP_PASSWORD=YOUR_MONGO_APP_PASSWORD_HERE

# Redis Authentication
REDIS_PASSWORD=YOUR_REDIS_PASSWORD_HERE

# Updated Connection Strings (replace PASSWORD with actual values)
MONGO_URI=mongodb://litecoin_app:YOUR_MONGO_APP_PASSWORD_HERE@mongodb:27017/litecoin_rag_db?authSource=litecoin_rag_db
MONGO_DETAILS=mongodb://litecoin_app:YOUR_MONGO_APP_PASSWORD_HERE@mongodb:27017/litecoin_rag_db?authSource=litecoin_rag_db
DATABASE_URI=mongodb://litecoin_app:YOUR_MONGO_APP_PASSWORD_HERE@mongodb:27017/payload_cms?authSource=payload_cms
REDIS_URL=redis://:YOUR_REDIS_PASSWORD_HERE@redis:6379/0
```

**Important Notes:**
- The `authSource` parameter tells MongoDB which database to authenticate against
- For `litecoin_rag_db`, use `authSource=litecoin_rag_db`
- For `payload_cms`, use `authSource=payload_cms`
- Redis password format: `redis://:password@host:port/db`

### Step 4: (Optional) Backup Your Data

Before enabling authentication, it's recommended to backup your MongoDB data:

```bash
# Backup MongoDB
docker exec litecoin-mongodb mongodump --out /data/backup
docker cp litecoin-mongodb:/data/backup ./mongodb-backup-$(date +%Y%m%d)

# Verify backup
ls -lh ./mongodb-backup-*
```

### Step 5: Stop Services

Stop your Docker Compose services:

```bash
# For production
docker-compose -f docker-compose.prod.yml down

# For development
docker-compose -f docker-compose.dev.yml down

# For prod-local
docker-compose -f docker-compose.prod-local.yml down
```

### Step 6: Start Services with Authentication

The Docker Compose files have already been updated to enable authentication. Simply start the services:

```bash
# For production
docker-compose -f docker-compose.prod.yml up -d

# For development
docker-compose -f docker-compose.dev.yml up -d

# For prod-local
docker-compose -f docker-compose.prod-local.yml down
```

The services will now start with authentication enabled.

### Step 7: Verify Authentication

#### Verify MongoDB Authentication

1. **Test without credentials (should fail):**
   ```bash
   docker exec -it litecoin-mongodb mongosh
   # Should show authentication error
   ```

2. **Test with credentials (should succeed):**
   ```bash
   docker exec -it litecoin-mongodb mongosh \
     -u admin \
     -p YOUR_MONGO_ROOT_PASSWORD_HERE \
     --authenticationDatabase admin
   # Should connect successfully
   ```

3. **Test application user:**
   ```bash
   docker exec -it litecoin-mongodb mongosh \
     -u litecoin_app \
     -p YOUR_MONGO_APP_PASSWORD_HERE \
     --authenticationDatabase litecoin_rag_db
   # Should connect successfully
   ```

#### Verify Redis Authentication

1. **Test without password (should fail):**
   ```bash
   docker exec -it litecoin-redis redis-cli
   # Try: GET test
   # Should show: (error) NOAUTH Authentication required
   ```

2. **Test with password (should succeed):**
   ```bash
   docker exec -it litecoin-redis redis-cli -a YOUR_REDIS_PASSWORD_HERE
   # Try: GET test
   # Should work
   ```

### Step 8: Verify Application Connectivity

1. **Check backend logs:**
   ```bash
   docker logs litecoin-backend
   # Should show successful MongoDB and Redis connections
   ```

2. **Check Payload CMS logs:**
   ```bash
   docker logs litecoin-payload-cms
   # Should show successful MongoDB connection
   ```

3. **Test application functionality:**
   - Access Payload CMS admin panel
   - Verify you can read/write articles
   - Test chat functionality (uses Redis for rate limiting)
   - Verify all data is accessible

## Troubleshooting

### MongoDB Won't Start

**Problem:** MongoDB container fails to start with authentication enabled.

**Solution:**
1. Check logs: `docker logs litecoin-mongodb`
2. Verify users were created before enabling `--auth`
3. If users don't exist, temporarily remove `--auth` from Docker Compose, create users, then re-enable

### "Authentication Failed" Errors

**Problem:** Applications can't connect to MongoDB/Redis.

**Solutions:**
1. **MongoDB:**
   - Verify connection string includes username, password, and `authSource`
   - Check that `MONGO_APP_PASSWORD` matches the password used when creating the user
   - Verify the user exists: `docker exec -it litecoin-mongodb mongosh -u admin -p ROOT_PASSWORD --authenticationDatabase admin` then `use admin; db.getUsers()`

2. **Redis:**
   - Verify `REDIS_URL` includes password: `redis://:password@redis:6379/0`
   - Or verify `REDIS_PASSWORD` environment variable is set
   - Check Redis logs: `docker logs litecoin-redis`

### Payload CMS Can't Access Data

**Problem:** Payload CMS connects but can't read/write data.

**Solution:**
1. Verify `DATABASE_URI` includes correct `authSource=payload_cms`
2. Verify the `litecoin_app` user has `readWrite` role on `payload_cms` database
3. Check Payload CMS logs for specific error messages

### Health Checks Failing

**Problem:** Docker health checks fail after enabling authentication.

**Solution:**
- Health checks have been updated in Docker Compose files to include authentication
- Verify `MONGO_ROOT_PASSWORD` is set in environment
- Check health check logs: `docker inspect litecoin-mongodb | grep -A 10 Health`

## Rollback Plan

If something goes wrong, you can temporarily disable authentication:

1. **Stop services:**
   ```bash
   docker-compose -f docker-compose.prod.yml down
   ```

2. **Temporarily remove `--auth` from MongoDB command in Docker Compose:**
   ```yaml
   # Change from:
   command: mongod --auth
   # To:
   # command: mongod
   ```

3. **Remove `--requirepass` from Redis command:**
   ```yaml
   # Change from:
   command: redis-server --requirepass ${REDIS_PASSWORD} ...
   # To:
   command: redis-server ...
   ```

4. **Update connection strings to remove credentials**

5. **Restart services**

**⚠️ WARNING:** Only do this for troubleshooting. Re-enable authentication before deploying to production.

## Security Best Practices

1. **Use strong passwords:** Always generate passwords with `openssl rand -base64 32` or similar
2. **Never commit passwords:** Keep passwords in `.env` files, never commit to git
3. **Rotate passwords regularly:** Change passwords periodically
4. **Use different passwords:** Use different passwords for root and app users
5. **Limit root access:** Only use root user for administration, use app user for applications
6. **Monitor access:** Check logs regularly for authentication failures

## Next Steps

After completing this migration:

1. ✅ Update security assessment: Mark CRIT-3 and CRIT-4 as resolved
2. ✅ Test all functionality thoroughly
3. ✅ Update deployment documentation
4. ✅ Consider implementing password rotation schedule
5. ✅ Set up monitoring for authentication failures

## Related Documentation

- [Environment Variables Documentation](./ENVIRONMENT_VARIABLES.md)
- [Red Team Security Assessment](./RED_TEAM_ASSESSMENT_COMBINED.md) - See CRIT-3 and CRIT-4
- [Docker Environment Switching Guide](./DOCKER_ENV_SWITCHING.md)

## Support

If you encounter issues during migration:

1. Check the troubleshooting section above
2. Review Docker container logs
3. Verify environment variables are set correctly
4. Ensure users were created before enabling authentication

---

**Migration completed?** Update the security assessment document to mark CRIT-3 and CRIT-4 as resolved! 🎉

