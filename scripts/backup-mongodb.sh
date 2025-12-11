#!/bin/bash

# MongoDB Backup Script
# This script backs up MongoDB databases (litecoin_rag_db and payload_cms).
# It is designed to use **local Docker MongoDB as the primary source of truth**,
# but can also talk to a remote/cloud MongoDB (e.g., Atlas) if MONGO_URI points there.
#
# Usage:
#   ./backup-mongodb.sh [--output-dir DIR] [--databases DB1,DB2]
#
# The script automatically detects MongoDB connection type from environment variables
# loaded from .env.docker.prod and .env.secrets files.

set -e  # Exit on error

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Default values
OUTPUT_DIR="$PROJECT_ROOT/mongodb-migration-backup"
DATABASES="litecoin_rag_db,payload_cms"
TIMESTAMP=$(date +"%Y-%m-%d-%H%M%S")
BACKUP_DIR="$OUTPUT_DIR/backup-$TIMESTAMP"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Show help
show_help() {
    cat << EOF
MongoDB Backup Script

This script backs up MongoDB databases from either local Docker or cloud Atlas.

Usage:
    $0 [OPTIONS]

Options:
    --output-dir DIR      Base directory for backups (default: ./mongodb-migration-backup)
    --databases LIST      Comma-separated list of databases to backup
                          (default: litecoin_rag_db,payload_cms)
    --help                Show this help message

Environment Variables:
    The script automatically loads from:
    - .env.docker.prod (if exists)
    - .env.secrets (if exists)
    
    Required variables:
    - MONGO_URI or MONGO_DETAILS - MongoDB connection string
    - DATABASE_URI - Payload CMS connection string (optional, uses MONGO_URI if not set)
    
    For local Docker MongoDB:
    - MONGO_INITDB_ROOT_USERNAME or MONGO_ROOT_USERNAME
    - MONGO_INITDB_ROOT_PASSWORD or MONGO_ROOT_PASSWORD

Examples:
    # Backup with defaults
    $0
    
    # Backup to custom directory
    $0 --output-dir /backups/mongodb
    
    # Backup specific databases
    $0 --databases "litecoin_rag_db"

Notes:
    - Ensure mongodump is installed (brew install mongodb-database-tools)
    - For local Docker, the MongoDB container must be running
    - Backups are stored in timestamped directories

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --output-dir)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            --databases)
                DATABASES="$2"
                shift 2
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Update backup directory with new output dir
    BACKUP_DIR="$OUTPUT_DIR/backup-$TIMESTAMP"
}

# Load environment variables from .env file
load_env_file() {
    local env_file="$1"
    if [ -f "$env_file" ]; then
        print_info "Loading environment variables from $(basename "$env_file")..."
        # Create a temporary file with filtered content (no comments, no empty lines)
        TEMP_ENV=$(mktemp)
        grep -v '^[[:space:]]*#' "$env_file" | grep -v '^[[:space:]]*$' > "$TEMP_ENV"
        
        # Source the filtered file
        set -a  # Automatically export all variables
        source "$TEMP_ENV"
        set +a
        
        # Clean up temp file
        rm -f "$TEMP_ENV"
        return 0
    else
        return 1
    fi
}

# Load environment variables
load_environment() {
    print_info "Loading environment variables..."
    
    # Load .env.docker.prod
    ENV_PROD_FILE="$PROJECT_ROOT/.env.docker.prod"
    if load_env_file "$ENV_PROD_FILE"; then
        print_info "✓ Loaded .env.docker.prod"
    else
        print_warn ".env.docker.prod not found, using environment variables from shell"
    fi
    
    # Load .env.secrets
    SECRETS_FILE="$PROJECT_ROOT/.env.secrets"
    if load_env_file "$SECRETS_FILE"; then
        print_info "✓ Loaded .env.secrets"
    else
        print_warn ".env.secrets not found (optional for cloud MongoDB)"
    fi
}

# Detect MongoDB connection type and extract connection details
detect_mongodb_connection() {
    # Check for MONGO_URI or MONGO_DETAILS
    MONGO_URI="${MONGO_URI:-${MONGO_DETAILS:-}}"
    
    if [ -z "$MONGO_URI" ]; then
        print_error "MONGO_URI or MONGO_DETAILS environment variable is not set"
        print_error "Please set it in .env.docker.prod or export it in your shell"
        exit 1
    fi
    
    print_info "Detected MongoDB URI: ${MONGO_URI%%@*}@***"  # Hide password
    
    # Detect connection type
    if [[ "$MONGO_URI" == mongodb+srv://* ]]; then
        CONNECTION_TYPE="cloud"
        print_info "Connection type: MongoDB Atlas (cloud)"
        BACKEND_URI="$MONGO_URI"
    elif [[ "$MONGO_URI" == mongodb://* ]]; then
        # Check if it's localhost or container name
        if [[ "$MONGO_URI" == *"localhost"* ]] || [[ "$MONGO_URI" == *"127.0.0.1"* ]] || [[ "$MONGO_URI" == *":27017"* ]]; then
            CONNECTION_TYPE="local"
            print_info "Connection type: Local MongoDB"
            
            # Check if MongoDB container is running
            if docker ps --format "{{.Names}}" | grep -q "litecoin-mongodb"; then
                CONTAINER_NAME="litecoin-mongodb"
                print_info "Found MongoDB container: $CONTAINER_NAME"
            elif docker ps --format "{{.Names}}" | grep -q "litecoin-mongodb-dev"; then
                CONTAINER_NAME="litecoin-mongodb-dev"
                print_info "Found MongoDB container: $CONTAINER_NAME"
            else
                print_warn "MongoDB container not found, assuming local MongoDB on host"
                CONTAINER_NAME=""
            fi
            
            # Extract connection details for local MongoDB
            # If URI doesn't have credentials, try to get them from env vars
            if [[ "$MONGO_URI" != *"@"* ]] || [[ "$MONGO_URI" == mongodb://:* ]]; then
                # No credentials in URI, try environment variables
                MONGO_USER="${MONGO_INITDB_ROOT_USERNAME:-${MONGO_ROOT_USERNAME:-}}"
                MONGO_PASS="${MONGO_INITDB_ROOT_PASSWORD:-${MONGO_ROOT_PASSWORD:-}}"
                
                if [ -n "$MONGO_USER" ] && [ -n "$MONGO_PASS" ]; then
                    # Extract host and port from URI
                    if [[ "$MONGO_URI" == mongodb://*"@"* ]]; then
                        # Has @ but no user:pass, extract host part
                        HOST_PORT=$(echo "$MONGO_URI" | sed 's/mongodb:\/\///' | sed 's/.*@//' | cut -d'/' -f1)
                    else
                        HOST_PORT=$(echo "$MONGO_URI" | sed 's/mongodb:\/\///' | cut -d'/' -f1)
                    fi
                    HOST_PORT="${HOST_PORT:-localhost:27017}"
                    BACKEND_URI="mongodb://${MONGO_USER}:${MONGO_PASS}@${HOST_PORT}/?authSource=admin"
                    print_info "Using authentication from environment variables"
                else
                    BACKEND_URI="$MONGO_URI"
                    print_warn "No authentication credentials found, using URI as-is"
                fi
            else
                BACKEND_URI="$MONGO_URI"
            fi
        else
            CONNECTION_TYPE="cloud"
            print_info "Connection type: Cloud MongoDB (non-Atlas)"
            BACKEND_URI="$MONGO_URI"
        fi
    else
        print_error "Unsupported MongoDB URI format: $MONGO_URI"
        exit 1
    fi
    
    # Get Payload CMS connection string
    if [ -n "${DATABASE_URI:-}" ]; then
        PAYLOAD_URI="$DATABASE_URI"
        print_info "Using DATABASE_URI for Payload CMS"
    else
        # Extract database name from MONGO_URI and replace with payload_cms
        if [[ "$BACKEND_URI" == *"/"* ]]; then
            PAYLOAD_URI=$(echo "$BACKEND_URI" | sed 's|/[^/]*\(?.*\)\?$|/payload_cms\1|')
        else
            PAYLOAD_URI="${BACKEND_URI}/payload_cms"
        fi
        print_info "Derived Payload CMS URI from MONGO_URI"
    fi
}

# Check if mongodump is available
check_mongodump() {
    if ! command -v mongodump &> /dev/null; then
        print_error "mongodump is not installed or not in PATH"
        print_info "Install MongoDB Database Tools:"
        print_info "  macOS: brew install mongodb-database-tools"
        print_info "  Linux: Download from https://www.mongodb.com/try/download/database-tools"
        exit 1
    fi
    print_info "✓ mongodump is available"
}

# Backup database using mongodump
backup_database() {
    local db_name=$1
    local connection_uri=$2
    local backup_path="$BACKUP_DIR/$db_name"
    
    print_info "Backing up database: $db_name"
    
    # Create backup directory
    mkdir -p "$backup_path"
    
    # Determine backup method based on connection type
    if [ "$CONNECTION_TYPE" = "local" ] && [ -n "$CONTAINER_NAME" ]; then
        # Use docker exec for local container
        print_info "Using Docker container: $CONTAINER_NAME"
        
        # Extract connection details for docker exec
        if [[ "$connection_uri" == mongodb://*"@"* ]]; then
            # Has credentials
            if docker exec "$CONTAINER_NAME" mongodump --uri="$connection_uri" --db="$db_name" --out=/data/backup 2>/dev/null; then
                # Copy backup from container
                docker cp "$CONTAINER_NAME:/data/backup/$db_name" "$backup_path" 2>/dev/null || {
                    print_error "Failed to copy backup from container"
                    return 1
                }
                print_info "✓ Successfully backed up $db_name from container"
                return 0
            else
                # Try without URI (if auth is not needed or different)
                print_warn "Failed with URI, trying without authentication..."
                if docker exec "$CONTAINER_NAME" mongodump --db="$db_name" --out=/data/backup 2>/dev/null; then
                    docker cp "$CONTAINER_NAME:/data/backup/$db_name" "$backup_path" 2>/dev/null || {
                        print_error "Failed to copy backup from container"
                        return 1
                    }
                    print_info "✓ Successfully backed up $db_name from container (no auth)"
                    return 0
                else
                    print_error "Failed to backup $db_name from container"
                    return 1
                fi
            fi
        else
            # No credentials, try direct dump
            if docker exec "$CONTAINER_NAME" mongodump --db="$db_name" --out=/data/backup 2>/dev/null; then
                docker cp "$CONTAINER_NAME:/data/backup/$db_name" "$backup_path" 2>/dev/null || {
                    print_error "Failed to copy backup from container"
                    return 1
                }
                print_info "✓ Successfully backed up $db_name from container"
                return 0
            else
                print_error "Failed to backup $db_name from container"
                return 1
            fi
        fi
    else
        # Use mongodump directly (cloud or local host)
        if mongodump --uri="$connection_uri" --db="$db_name" --out="$backup_path" 2>/dev/null; then
            print_info "✓ Successfully backed up $db_name"
            return 0
        else
            print_error "Failed to backup $db_name"
            return 1
        fi
    fi
}

# Get database connection URI for a specific database
get_database_uri() {
    local db_name=$1
    local base_uri=$2
    
    # If URI already has a database name, replace it
    if [[ "$base_uri" == *"/"* ]] && [[ "$base_uri" != *"?"* ]] || [[ "$base_uri" == *"/"*"?"* ]]; then
        # Has database name, replace it
        echo "$base_uri" | sed "s|/[^/?]*\(?.*\)\?$|/$db_name\1|"
    else
        # No database name, append it
        if [[ "$base_uri" == *"?"* ]]; then
            # Has query parameters
            echo "${base_uri%?}/$db_name?${base_uri#*?}"
        else
            # No query parameters
            echo "$base_uri/$db_name"
        fi
    fi
}

# Verify backup integrity
verify_backup() {
    local db_name=$1
    local backup_path="$BACKUP_DIR/$db_name"
    
    if [ ! -d "$backup_path" ]; then
        print_error "Backup directory not found: $backup_path"
        return 1
    fi
    
    # Check if backup has collections
    if [ -z "$(ls -A "$backup_path" 2>/dev/null)" ]; then
        print_warn "Backup directory is empty: $backup_path"
        return 1
    fi
    
    # Count collections
    collection_count=$(find "$backup_path" -type d -mindepth 1 -maxdepth 1 | wc -l | tr -d ' ')
    if [ "$collection_count" -gt 0 ]; then
        print_info "✓ Backup verified: $collection_count collection(s) found"
        return 0
    else
        print_warn "Backup may be empty or invalid"
        return 1
    fi
}

# Calculate backup size
get_backup_size() {
    local backup_path="$1"
    if [ -d "$backup_path" ]; then
        du -sh "$backup_path" 2>/dev/null | cut -f1
    else
        echo "0"
    fi
}

# Main backup function
main() {
    print_header "MongoDB Backup Script"
    
    # Parse arguments
    parse_args "$@"
    
    # Load environment variables
    load_environment
    
    # Detect MongoDB connection
    detect_mongodb_connection
    
    # Check mongodump
    check_mongodump
    
    # Create backup directory
    mkdir -p "$BACKUP_DIR"
    print_info "Backup directory: $BACKUP_DIR"
    
    # Convert comma-separated databases to array
    IFS=',' read -ra DB_ARRAY <<< "$DATABASES"
    
    print_header "Starting Backup Process"
    
    backup_success=true
    backup_results=()
    
    # Backup each database
    for db in "${DB_ARRAY[@]}"; do
        db=$(echo "$db" | xargs)  # Trim whitespace
        
        echo ""
        print_info "=== Backing up: $db ==="
        
        # Determine which connection URI to use
        if [ "$db" = "payload_cms" ]; then
            db_uri=$(get_database_uri "$db" "$PAYLOAD_URI")
        else
            db_uri=$(get_database_uri "$db" "$BACKEND_URI")
        fi
        
        if backup_database "$db" "$db_uri"; then
            if verify_backup "$db"; then
                size=$(get_backup_size "$BACKUP_DIR/$db")
                backup_results+=("✓ $db: $size")
            else
                backup_results+=("⚠ $db: Backup created but verification failed")
                backup_success=false
            fi
        else
            backup_results+=("✗ $db: Backup failed")
            backup_success=false
        fi
    done
    
    # Print summary
    echo ""
    print_header "Backup Summary"
    
    for result in "${backup_results[@]}"; do
        if [[ "$result" == "✓"* ]]; then
            print_info "$result"
        elif [[ "$result" == "⚠"* ]]; then
            print_warn "$result"
        else
            print_error "$result"
        fi
    done
    
    echo ""
    print_info "Backup location: $BACKUP_DIR"
    
    total_size=$(get_backup_size "$BACKUP_DIR")
    print_info "Total backup size: $total_size"
    
    if [ "$backup_success" = true ]; then
        print_info "✓ All backups completed successfully!"
        exit 0
    else
        print_error "Some backups failed. Please check the output above."
        exit 1
    fi
}

# Run main function
main "$@"

