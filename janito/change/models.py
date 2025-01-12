class ChangeOperation:
    CREATE_FILE = 'create_file'
    MODIFY_FILE = 'modify_file'
    DELETE_FILE = 'delete_file'
    RENAME_FILE = 'rename_file'

class FileChange:
    def __init__(self, name: str, operation: ChangeOperation, target: str):
        self.name = name
        self.operation = operation
        self.target = target
