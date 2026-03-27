# File Tools

janito provides tools for file operations on your local filesystem.

## Available Tools

| Tool | Description |
|------|-------------|
| `list_files` | List files and directories |
| `read_file` | Read file contents |
| `read_file_lines` | Read specific lines from a file |
| `read_multiple_files` | Read multiple files at once |
| `create_file` | Create a new file |
| `replace_text_in_file` | Replace text in a file |
| `delete_file` | Delete a file |
| `create_directory` | Create a directory |
| `remove_directory` | Remove a directory |
| `move_file` | Move or rename a file |
| `search_text` | Search for text in files |
| `search_regex` | Search using regular expressions |

## Examples

### List Files

```bash
janito "List all Python files in the current directory"
```

```python
from janito.tools.files import ListFiles

tool = ListFiles()
result = tool.run(path=".", pattern="*.py", recursive=True)
```

### Read a File

```bash
janito "Read the first 20 lines of README.md"
```

```python
from janito.tools.files import ReadFile

tool = ReadFile()
result = tool.run(filepath="README.md", max_lines=20)
```

### Create a File

```bash
janito "Create a new file called hello.py with print('Hello, World!')"
```

```python
from janito.tools.files import CreateFile

tool = CreateFile()
result = tool.run(filepath="hello.py", content="print('Hello, World!')")
```

### Search in Files

```bash
janito "Find all files containing 'TODO' in the project"
```

```python
from janito.tools.files import SearchText

tool = SearchText()
result = tool.run(path=".", query="TODO", case_sensitive=False)
```

### Replace Text

```bash
janito "Replace 'old text' with 'new text' in file.txt"
```

```python
from janito.tools.files import ReplaceTextInFile

tool = ReplaceTextInFile()
result = tool.run(filepath="file.txt", old_str="old text", new_str="new text")
```

## CLI Access

You can also use file tools directly from the command line:

```bash
# List files
python -m janito.tools.files list-files . --recursive --pattern "*.py"

# Read file
python -m janito.tools.files read-file README.md --max-lines 20

# Create directory
python -m janito.tools.files create-directory new_folder
```

## Safety

- **Always read before write**: Use `read_file` first to check existing content
- **Confirm paths**: Verify file paths before operations
- **Use dry runs**: Some tools support preview mode before making changes
