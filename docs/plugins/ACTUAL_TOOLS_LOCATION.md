# Actual Tools Location

## Real Tool Implementations

The actual tool implementations are located in:
```
janito/tools/adapters/local/
```

## Tool Mapping

| Plugin Name | Actual Tool File | Description |
|-------------|------------------|-------------|
| **core.filemanager** | | |
| `create_file` | `janito/tools/adapters/local/create_file.py` | Create new files |
| `read_files` | `janito/tools/adapters/local/read_files.py` | Read multiple files |
| `view_file` | `janito/tools/adapters/local/view_file.py` | Read file contents |
| `replace_text_in_file` | `janito/tools/adapters/local/replace_text_in_file.py` | Find and replace text |
| `validate_file_syntax` | `janito/tools/adapters/local/validate_file_syntax/` | Syntax validation |
| `create_directory` | `janito/tools/adapters/local/create_directory.py` | Create directories |
| `remove_directory` | `janito/tools/adapters/local/remove_directory.py` | Remove directories |
| `remove_file` | `janito/tools/adapters/local/remove_file.py` | Delete files |
| `copy_file` | `janito/tools/adapters/local/copy_file.py` | Copy files/directories |
| `move_file` | `janito/tools/adapters/local/move_file.py` | Move/rename files |
| `find_files` | `janito/tools/adapters/local/find_files.py` | Search for files |
| **core.codeanalyzer** | | |
| `get_file_outline` | `janito/tools/adapters/local/get_file_outline/` | File structure analysis |
| `search_outline` | `janito/tools/adapters/local/get_file_outline/search_outline.py` | Search in outlines |
| `search_text` | `janito/tools/adapters/local/search_text/` | Text search |
| **core.system** | | |
| `run_powershell_command` | `janito/tools/adapters/local/run_powershell_command.py` | PowerShell execution |
| **web.webtools** | | |
| `fetch_url` | `janito/tools/adapters/local/fetch_url.py` | Web scraping |
| `open_url` | `janito/tools/adapters/local/open_url.py` | Open URLs |
| `open_html_in_browser` | `janito/tools/adapters/local/open_html_in_browser.py` | Open HTML files |
| **dev.pythondev** | | |
| `python_code_run` | `janito/tools/adapters/local/python_code_run.py` | Python execution |
| `python_command_run` | `janito/tools/adapters/local/python_command_run.py` | Python -c execution |
| `python_file_run` | `janito/tools/adapters/local/python_file_run.py` | Python script execution |
| **dev.visualization** | | |
| `read_chart` | `janito/tools/adapters/local/read_chart.py` | Data visualization |
| **core.imagedisplay** | | |
| `show_image` | `janito/tools/adapters/local/show_image.py` | Display single image |
| `show_image_grid` | `janito/tools/adapters/local/show_image_grid.py` | Display multiple images in a grid |
| **ui.userinterface** | | |
| `ask_user` | `janito/tools/adapters/local/ask_user.py` | User interaction |

## Architecture Note

The plugin system in `plugins/` contains **interface definitions and wrappers**, while the actual tool implementations are in `janito/tools/adapters/local/`. 

The real tools are implemented as classes inheriting from `ToolBase` and registered via decorators like `@register_local_tool`.