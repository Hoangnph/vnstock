#!/bin/bash

# StockAI Database Backup Script
# This script creates automated backups of the StockAI database

set -e

# Configuration
DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-stockai}"
DB_USER="${DB_USER:-stockai_user}"
DB_PASSWORD="${DB_PASSWORD:-stockai_password_2025}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/stockai_backup_${TIMESTAMP}.sql"
LOG_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Function to check if database is accessible
check_database() {
    log "Checking database connectivity..."
    if ! PGPASSWORD="$DB_PASSWORD" pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" > /dev/null 2>&1; then
        error "Database is not accessible. Please check connection parameters."
        exit 1
    fi
    log "Database connectivity check passed."
}

# Function to create full database backup
create_backup() {
    log "Starting database backup..."
    log "Backup file: $BACKUP_FILE"
    
    # Create backup with custom format for better compression
    if PGPASSWORD="$DB_PASSWORD" pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --verbose \
        --no-password \
        --format=custom \
        --compress=9 \
        --file="${BACKUP_FILE}.dump" 2>&1 | tee -a "$LOG_FILE"; then
        
        log "Database backup completed successfully."
        
        # Also create a plain SQL backup for easy inspection
        if PGPASSWORD="$DB_PASSWORD" pg_dump \
            -h "$DB_HOST" \
            -p "$DB_PORT" \
            -U "$DB_USER" \
            -d "$DB_NAME" \
            --verbose \
            --no-password \
            --format=plain \
            --file="$BACKUP_FILE" 2>&1 | tee -a "$LOG_FILE"; then
            
            log "Plain SQL backup completed successfully."
        else
            warning "Plain SQL backup failed, but custom format backup succeeded."
        fi
        
        # Get backup file sizes
        if [ -f "${BACKUP_FILE}.dump" ]; then
            DUMP_SIZE=$(du -h "${BACKUP_FILE}.dump" | cut -f1)
            log "Custom format backup size: $DUMP_SIZE"
        fi
        
        if [ -f "$BACKUP_FILE" ]; then
            SQL_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
            log "Plain SQL backup size: $SQL_SIZE"
        fi
        
    else
        error "Database backup failed."
        exit 1
    fi
}

# Function to create schema-only backup
create_schema_backup() {
    local schema_file="${BACKUP_DIR}/stockai_schema_${TIMESTAMP}.sql"
    log "Creating schema-only backup: $schema_file"
    
    if PGPASSWORD="$DB_PASSWORD" pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --schema-only \
        --no-password \
        --file="$schema_file" 2>&1 | tee -a "$LOG_FILE"; then
        
        log "Schema backup completed successfully."
        local schema_size=$(du -h "$schema_file" | cut -f1)
        log "Schema backup size: $schema_size"
    else
        warning "Schema backup failed."
    fi
}

# Function to create data-only backup
create_data_backup() {
    local data_file="${BACKUP_DIR}/stockai_data_${TIMESTAMP}.sql"
    log "Creating data-only backup: $data_file"
    
    if PGPASSWORD="$DB_PASSWORD" pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --data-only \
        --no-password \
        --file="$data_file" 2>&1 | tee -a "$LOG_FILE"; then
        
        log "Data backup completed successfully."
        local data_size=$(du -h "$data_file" | cut -f1)
        log "Data backup size: $data_size"
    else
        warning "Data backup failed."
    fi
}

# Function to clean up old backups
cleanup_old_backups() {
    log "Cleaning up backups older than $RETENTION_DAYS days..."
    
    local deleted_count=0
    
    # Delete old backup files
    while IFS= read -r -d '' file; do
        if rm "$file"; then
            ((deleted_count++))
            log "Deleted old backup: $(basename "$file")"
        else
            warning "Failed to delete: $(basename "$file")"
        fi
    done < <(find "$BACKUP_DIR" -name "stockai_backup_*.sql" -type f -mtime +$RETENTION_DAYS -print0)
    
    # Delete old dump files
    while IFS= read -r -d '' file; do
        if rm "$file"; then
            ((deleted_count++))
            log "Deleted old dump: $(basename "$file")"
        else
            warning "Failed to delete: $(basename "$file")"
        fi
    done < <(find "$BACKUP_DIR" -name "stockai_backup_*.dump" -type f -mtime +$RETENTION_DAYS -print0)
    
    # Delete old log files
    while IFS= read -r -d '' file; do
        if rm "$file"; then
            ((deleted_count++))
            log "Deleted old log: $(basename "$file")"
        else
            warning "Failed to delete: $(basename "$file")"
        fi
    done < <(find "$BACKUP_DIR" -name "backup_*.log" -type f -mtime +$RETENTION_DAYS -print0)
    
    if [ $deleted_count -eq 0 ]; then
        log "No old backups found to clean up."
    else
        log "Cleaned up $deleted_count old backup files."
    fi
}

# Function to show backup statistics
show_backup_stats() {
    log "Backup Statistics:"
    log "=================="
    
    # Count total backups
    local total_backups=$(find "$BACKUP_DIR" -name "stockai_backup_*.sql" -type f | wc -l)
    local total_dumps=$(find "$BACKUP_DIR" -name "stockai_backup_*.dump" -type f | wc -l)
    
    log "Total SQL backups: $total_backups"
    log "Total dump backups: $total_dumps"
    
    # Show disk usage
    local total_size=$(du -sh "$BACKUP_DIR" | cut -f1)
    log "Total backup directory size: $total_size"
    
    # Show latest backups
    log "Latest backups:"
    find "$BACKUP_DIR" -name "stockai_backup_*.sql" -type f -printf "%T@ %Tc %p\n" | sort -nr | head -5 | while read -r timestamp date file; do
        local size=$(du -h "$file" | cut -f1)
        log "  $(basename "$file") - $size - $date"
    done
}

# Function to restore from backup
restore_backup() {
    local backup_file="$1"
    
    if [ -z "$backup_file" ]; then
        error "Please specify a backup file to restore from."
        echo "Usage: $0 restore <backup_file>"
        exit 1
    fi
    
    if [ ! -f "$backup_file" ]; then
        error "Backup file not found: $backup_file"
        exit 1
    fi
    
    log "Restoring database from: $backup_file"
    warning "This will overwrite the current database. Are you sure? (y/N)"
    read -r confirmation
    
    if [[ $confirmation =~ ^[Yy]$ ]]; then
        if PGPASSWORD="$DB_PASSWORD" pg_restore \
            -h "$DB_HOST" \
            -p "$DB_PORT" \
            -U "$DB_USER" \
            -d "$DB_NAME" \
            --verbose \
            --clean \
            --if-exists \
            "$backup_file" 2>&1 | tee -a "$LOG_FILE"; then
            
            log "Database restore completed successfully."
        else
            error "Database restore failed."
            exit 1
        fi
    else
        log "Restore cancelled by user."
    fi
}

# Main function
main() {
    case "${1:-backup}" in
        "backup")
            log "Starting StockAI database backup process..."
            check_database
            create_backup
            create_schema_backup
            create_data_backup
            cleanup_old_backups
            show_backup_stats
            log "Backup process completed successfully."
            ;;
        "restore")
            restore_backup "$2"
            ;;
        "cleanup")
            cleanup_old_backups
            show_backup_stats
            ;;
        "stats")
            show_backup_stats
            ;;
        "test")
            log "Testing database connectivity..."
            check_database
            log "Database connectivity test passed."
            ;;
        *)
            echo "Usage: $0 {backup|restore|cleanup|stats|test}"
            echo ""
            echo "Commands:"
            echo "  backup   - Create full database backup (default)"
            echo "  restore  - Restore database from backup file"
            echo "  cleanup  - Clean up old backup files"
            echo "  stats    - Show backup statistics"
            echo "  test     - Test database connectivity"
            echo ""
            echo "Environment variables:"
            echo "  DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD"
            echo "  BACKUP_DIR, RETENTION_DAYS"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
