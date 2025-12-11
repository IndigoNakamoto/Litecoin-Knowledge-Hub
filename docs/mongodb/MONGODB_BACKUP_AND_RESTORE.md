## MongoDB Backup & Restore

This project includes a small, scriptable workflow for taking MongoDB backups and restoring them into any MongoDB instance (local Docker, another server, or cloud).

The main script is `scripts/backup-mongodb.sh`. It:
- Loads Mongo connection details from `.env.docker.prod` and `.env.secrets` (if present).
- Detects whether it is talking to a local Docker MongoDB or a remote/cloud MongoDB.
- Dumps two databases by default:
  - `litecoin_rag_db`
  - `payload_cms`
- Writes each backup into a timestamped directory under `mongodb-migration-backup/backup-<YYYY-MM-DD-HHMMSS>/`.

At the time of writing, there is an existing backup created from the cloud MongoDB instance in:

- `mongodb-migration-backup/backup-2025-12-10-002240`

Treat that directory as a known-good snapshot of the cloud state that you can restore into a new local MongoDB.

---

## Taking a New Backup

From the project root:

```bash
cd /Users/indigo/Projects/Litecoin-Knowledge-Hub
./scripts/backup-mongodb.sh
```

This will:
- Load MongoDB connection settings from `.env.docker.prod` / `.env.secrets`.
- Create a new directory: `mongodb-migration-backup/backup-<TIMESTAMP>/`.
- Dump `litecoin_rag_db` and `payload_cms` into that directory.

> Note: The script can also be pointed at a non-local/Atlas URI by setting `MONGO_URI` and `DATABASE_URI` in your environment or `.env.docker.prod`. Going forward we default these to point at the **local Docker MongoDB**.

---

## Restoring a Backup into a MongoDB Instance (Docker)

You can restore any `backup-<TIMESTAMP>` directory into a MongoDB instance using the official `mongo` Docker image and `mongorestore`.

Assuming:
- You are in the project root: `/Users/indigo/Projects/Litecoin-Knowledge-Hub`.
- You want to restore the snapshot from `mongodb-migration-backup/backup-2025-12-10-002240`.
- You have a running MongoDB container called `mongodb` on `localhost:27017` (for example, from `docker-compose.prod-local.yml`).

Run:

```bash
cd /Users/indigo/Projects/Litecoin-Knowledge-Hub

BACKUP_DIR="mongodb-migration-backup/backup-2025-12-10-002240"

# Restore litecoin_rag_db into the target MongoDB
docker run --rm \
  -v "$PWD/$BACKUP_DIR":/dump \
  --network=host \
  mongo:6.0 \
  mongorestore --uri "mongodb://localhost:27017/litecoin_rag_db" /dump/litecoin_rag_db

# Restore payload_cms into the target MongoDB
docker run --rm \
  -v "$PWD/$BACKUP_DIR":/dump \
  --network=host \
  mongo:6.0 \
  mongorestore --uri "mongodb://localhost:27017/payload_cms" /dump/payload_cms
```

If your MongoDB requires authentication, adjust the `--uri` values accordingly:

```bash
mongorestore --uri "mongodb://USERNAME:PASSWORD@localhost:27017/litecoin_rag_db?authSource=admin" /dump/litecoin_rag_db
```

---

## Restoring into Docker Compose `mongodb` Service

If MongoDB is running as the `mongodb` service inside `docker-compose.prod-local.yml`, you can restore directly into that service by using the default internal hostname `mongodb`:

```bash
BACKUP_DIR="mongodb-migration-backup/backup-2025-12-10-002240"

docker run --rm \
  -v "$PWD/$BACKUP_DIR":/dump \
  --network=litecoin-knowledge-hub_default \
  mongo:6.0 \
  mongorestore --uri "mongodb://mongodb:27017/litecoin_rag_db" /dump/litecoin_rag_db

docker run --rm \
  -v "$PWD/$BACKUP_DIR":/dump \
  --network=litecoin-knowledge-hub_default \
  mongo:6.0 \
  mongorestore --uri "mongodb://mongodb:27017/payload_cms" /dump/payload_cms
```

Replace `litecoin-knowledge-hub_default` with the actual Docker network name if it differs (`docker network ls` to check).

---

## Disaster Recovery Notes

If you lose your main machine but still have:
- This repository cloned somewhere, and
- An offsite copy of `mongodb-migration-backup/backup-<TIMESTAMP>/` (or an encrypted archive of it),

then any developer can:
1. Bring up a new MongoDB (local Docker or remote).
2. Use `mongorestore` as shown above to restore `litecoin_rag_db` and `payload_cms`.
3. Point the backend and Payload CMS at that MongoDB instance via `MONGO_URI` and `DATABASE_URI`.

This is the core of the “house burns down, another dev can rebuild from the cloud” story.

---

## Encrypted Offsite Backups to GitHub (Recommended)

For a tiny database (~MBs), you can cheaply keep encrypted backups in a private GitHub repo.

### One-Time Setup

1. Install an encryption tool (prefer `age`, fall back to `gpg`):
   - `age`: see the official docs, generate a keypair and store the private key in your password manager.
   - `gpg`: ensure you have a keypair and know your key ID or email.
2. Configure one of:
   - `AGE_BACKUP_RECIPIENT` (your age public recipient string), or
   - `MONGODB_BACKUP_GPG_RECIPIENT` (your GPG recipient, email or key ID).

You can export these in your shell profile or set them just before running the scripts.

### Run: Backup + Encrypt + Stage for GitHub

From the project root:

```bash
cd /Users/indigo/Projects/Litecoin-Knowledge-Hub
./scripts/backup-and-stage-for-github.sh
```

This will:
- Run `scripts/backup-mongodb.sh` to create a fresh dump under `mongodb-migration-backup/backup-<TIMESTAMP>/`.
- Run `scripts/archive-encrypt-mongodb-backup.sh` to:
  - Create `mongodb-backup-<TIMESTAMP>.tar.gz` from that directory.
  - Encrypt it with `age` or `gpg` into `encrypted-backups/`.
- Print suggested `git add` / `git commit` / `git push` commands.

Typical follow-up:

```bash
git add encrypted-backups/
git commit -m "chore: mongo backup <TIMESTAMP>"
git push
```

### Restoring from an Encrypted Backup

On any new machine:

1. Clone the repo that contains `encrypted-backups/`.
2. Decrypt the archive (example with age):

```bash
age -d -o mongodb-backup.tar.gz encrypted-backups/mongodb-backup-<TIMESTAMP>.tar.gz.age
tar -xzf mongodb-backup.tar.gz
```

This will recreate `mongodb-migration-backup/backup-<TIMESTAMP>/` (or you can move it there).

3. Use the restore commands from earlier sections to load `litecoin_rag_db` and `payload_cms` into a MongoDB instance.


