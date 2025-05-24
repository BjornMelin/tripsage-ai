"""
File handling configuration constants.

Centralizes file validation and processing constants following KISS principles.
"""

# File size limits
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB per file
MAX_FILES_PER_REQUEST = 5
MAX_SESSION_SIZE = 50 * 1024 * 1024  # 50MB total per session

# Allowed file extensions
ALLOWED_EXTENSIONS = {
    ".pdf",
    ".txt",
    ".csv",
    ".json",  # Documents
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",  # Images
    ".docx",  # Office documents
    ".zip",  # Archives
}

# Allowed MIME types
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "text/plain",
    "text/csv",
    "application/json",
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/zip",
}

# File type categorization
FILE_TYPE_MAPPING = {
    # Images
    "image/jpeg": "image",
    "image/png": "image",
    "image/webp": "image",
    "image/gif": "image",
    # Documents
    "application/pdf": "document",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": (
        "document"
    ),
    # Text files
    "text/plain": "text",
    "text/csv": "spreadsheet",
    "application/json": "text",
    # Archives
    "application/zip": "archive",
}

# Storage configuration
DEFAULT_STORAGE_ROOT = "uploads"
TEMP_UPLOAD_DIR = "temp"
PROCESSED_DIR = "processed"
