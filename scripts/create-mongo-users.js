// MongoDB User Creation Script
// This script creates users for MongoDB authentication.
// Run this BEFORE enabling --auth flag in MongoDB.
//
// Usage:
//   docker exec -i litecoin-mongodb mongosh < scripts/create-mongo-users.js
//
// Or with environment variables:
//   docker exec -i -e MONGO_ROOT_USERNAME=admin -e MONGO_ROOT_PASSWORD=xxx -e MONGO_APP_USERNAME=litecoin_app -e MONGO_APP_PASSWORD=xxx litecoin-mongodb mongosh < scripts/create-mongo-users.js

// Get environment variables (passed via docker exec -e or set in container)
const rootUsername = process.env.MONGO_ROOT_USERNAME || 'admin';
const rootPassword = process.env.MONGO_ROOT_PASSWORD;
const appUsername = process.env.MONGO_APP_USERNAME || 'litecoin_app';
const appPassword = process.env.MONGO_APP_PASSWORD;

if (!rootPassword) {
  print('ERROR: MONGO_ROOT_PASSWORD environment variable must be set');
  quit(1);
}

if (!appPassword) {
  print('ERROR: MONGO_APP_PASSWORD environment variable must be set');
  quit(1);
}

print('Creating MongoDB users...');

// Create root admin user
try {
  db = db.getSiblingDB('admin');
  db.createUser({
    user: rootUsername,
    pwd: rootPassword,
    roles: [{ role: 'root', db: 'admin' }]
  });
  print(`✓ Created root user: ${rootUsername}`);
} catch (e) {
  if (e.code === 51003) {
    print(`⚠ Root user ${rootUsername} already exists, skipping...`);
  } else {
    print(`✗ Error creating root user: ${e.message}`);
    throw e;
  }
}

// Create application user for litecoin_rag_db
try {
  db = db.getSiblingDB('litecoin_rag_db');
  db.createUser({
    user: appUsername,
    pwd: appPassword,
    roles: [
      { role: 'readWrite', db: 'litecoin_rag_db' },
      { role: 'readWrite', db: 'payload_cms' }
    ]
  });
  print(`✓ Created app user: ${appUsername} for litecoin_rag_db`);
} catch (e) {
  if (e.code === 51003) {
    print(`⚠ App user ${appUsername} already exists in litecoin_rag_db, skipping...`);
  } else {
    print(`✗ Error creating app user in litecoin_rag_db: ${e.message}`);
    throw e;
  }
}

// Create application user for payload_cms (same user, different database)
try {
  db = db.getSiblingDB('payload_cms');
  db.createUser({
    user: appUsername,
    pwd: appPassword,
    roles: [{ role: 'readWrite', db: 'payload_cms' }]
  });
  print(`✓ Created app user: ${appUsername} for payload_cms`);
} catch (e) {
  if (e.code === 51003) {
    print(`⚠ App user ${appUsername} already exists in payload_cms, skipping...`);
  } else {
    print(`✗ Error creating app user in payload_cms: ${e.message}`);
    throw e;
  }
}

print('\n✓ All users created successfully!');
print('\nNext steps:');
print('1. Update Docker Compose files to add --auth flag to MongoDB command');
print('2. Update environment files with connection strings including credentials');
print('3. Restart services');

