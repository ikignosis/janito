from enum import Enum, auto

class TextOperation(Enum):
    """Supported text modification operations"""
    REPLACE = auto()
    APPEND = auto()
    DELETE = auto()

class FileOperation(Enum):
    """Supported file operations"""
    CREATE = auto()
    REPLACE = auto()
    REMOVE = auto()
    RENAME = auto()
    MOVE = auto()

    @property
    def requires_content(self) -> bool:
        """Check if operation requires content"""
        return self in (FileOperation.CREATE, FileOperation.REPLACE)

    @property
    def requires_target(self) -> bool:
        """Check if operation requires target path"""
        return self in (FileOperation.RENAME, FileOperation.MOVE)

