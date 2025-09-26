"""Qt logging configuration constants."""

# Qt Logging Configuration
QT_LOG_MAX_FILE_SIZE: int = 5 * 1024 * 1024  # 5MB per log file
QT_LOG_BACKUP_COUNT: int = 5  # Keep 5 backup files
QT_LOG_CATEGORIES: dict[str, str] = {
    "UI": "app.ui",
    "API": "app.api",
    "DOWNLOAD": "app.download",
    "THREAD": "app.threads",
    "ERROR": "app.error",
}
