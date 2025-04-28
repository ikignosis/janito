# Arquivo base de mensagens para i18n
# Chave = SHA-1 da string original em inglês

MESSAGES = {
    # create_directory.py
    "e3d8e1e5e0b3e4a2a7a5e2e1e4e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0": "Successfully created the directory at '{path}'.",
    "f2b7e4e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1": "Cannot create directory: '{path}' already exists.",
    "d3e2e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5": "Path '{path}' exists and is not a directory.",
    "b1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1": "Error creating directory '{path}': {error}",
    # create_file.py
    "a2e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0": "File already exists at '{path}'. Use overwrite=True to overwrite.",
    "c3e2e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5": "Created file ({lines} lines).",
    "d4e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0": "Updated file ({lines} lines, backup at {backup_path}).",
    # remove_file.py
    "e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5": "File '{path}' does not exist.",
    "f6e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0": "Path '{path}' is not a file.",
    "a7e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1": "Successfully removed the file at '{path}'.",
    "b8e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0": "Error removing file: {error}",
    # replace_text_in_file.py (exemplo)
    "c9e2e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5": "Text replaced in {file_path} (backup at {backup_path}). {details}",
    "d0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0": "No changes made. {warning_detail}",
    "e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1e5e0e1": "Error replacing text: {error}",
}
