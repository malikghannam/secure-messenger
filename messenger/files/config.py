"""Configuration for supported file types in secure file sharing."""

# File size constants (in bytes)
MB = 1024 * 1024

# Supported file types with their configurations
SUPPORTED_FILE_TYPES = {
    # Images - max 10 MB
    'image/png': {
        'extension': '.png',
        'max_size': 10 * MB,
        'category': 'image'
    },
    'image/jpeg': {
        'extension': '.jpg',
        'max_size': 10 * MB,
        'category': 'image'
    },
    'image/gif': {
        'extension': '.gif',
        'max_size': 10 * MB,
        'category': 'image'
    },
    'image/webp': {
        'extension': '.webp',
        'max_size': 10 * MB,
        'category': 'image'
    },
    
    # Documents - max 25 MB
    'application/pdf': {
        'extension': '.pdf',
        'max_size': 25 * MB,
        'category': 'document'
    },
    
    # Audio - max 15 MB
    'audio/mpeg': {
        'extension': '.mp3',
        'max_size': 15 * MB,
        'category': 'audio'
    },
    'audio/wav': {
        'extension': '.wav',
        'max_size': 15 * MB,
        'category': 'audio'
    },
    'audio/ogg': {
        'extension': '.ogg',
        'max_size': 15 * MB,
        'category': 'audio'
    },
    
    # Text - max 5 MB
    'text/plain': {
        'extension': '.txt',
        'max_size': 5 * MB,
        'category': 'text'
    },
    'application/json': {
        'extension': '.json',
        'max_size': 5 * MB,
        'category': 'text'
    },
    'application/xml': {
        'extension': '.xml',
        'max_size': 5 * MB,
        'category': 'text'
    },
}


def get_max_size_for_type(mime_type: str) -> int:
    """Get maximum file size for a MIME type."""
    if mime_type in SUPPORTED_FILE_TYPES:
        return SUPPORTED_FILE_TYPES[mime_type]['max_size']
    return 0


def is_supported_type(mime_type: str) -> bool:
    """Check if a MIME type is supported."""
    return mime_type in SUPPORTED_FILE_TYPES


def get_category(mime_type: str) -> str:
    """Get the category for a MIME type."""
    if mime_type in SUPPORTED_FILE_TYPES:
        return SUPPORTED_FILE_TYPES[mime_type]['category']
    return 'unknown'


def get_extension(mime_type: str) -> str:
    """Get the file extension for a MIME type."""
    if mime_type in SUPPORTED_FILE_TYPES:
        return SUPPORTED_FILE_TYPES[mime_type]['extension']
    return ''
