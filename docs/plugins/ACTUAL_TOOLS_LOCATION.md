# Actual Tools Location

## Real Tool Implementations

The actual tool implementations are located in:
```
janito/plugins/tools/local/
```

## Tool Mapping

| Plugin Name | Actual Tool File | Description |
|-------------|------------------|-------------|
| **core.filemanager** | | |
| `create_file` | `janito/plugins/tools/local/create_file.py` | Create new files |
| `read_files` | `janito/plugins/tools/local/read_files.py` | Read multiple files |
| `view_file` | `janito/plugins/tools/local/view_file.py` | Read file contents |
| `replace_text_in_file` | `janito/plugins/tools/local/replace_text_in_file.py` | Find and replace text |
| `validate_file_syntax` | `janito/plugins/tools/local/validate_file_syntax/` | Syntax validation |
| `create_directory` | `janito/plugins/tools/local/create_directory.py` | Create directories |
| `remove_directory` | `janito/plugins/tools/local/remove_directory.py` | Remove directories |
| `remove_file` | `janito/plugins/tools/local/remove_file.py` | Delete files |
| `copy_file` | `janito/plugins/tools/local/copy_file.py` | Copy files/directories |
| `move_file` | `janito/plugins/tools/local/move_file.py` | Move/rename files |
| `find_files` | `janito/plugins/tools/local/find_files.py` | Search for files |
| **core.codeanalyzer** | | |
| `get_file_outline` | `janito/plugins/tools/local/get_file_outline/` | File structure analysis |
| `search_outline` | `janito/plugins/tools/local/get_file_outline/search_outline.py` | Search in outlines |
| `search_text` | `janito/plugins/tools/local/search_text/` | Text search |
| **core.system** | | |
| `run_powershell_command` | `janito/plugins/tools/local/run_powershell_command.py` | PowerShell execution |
| **web.webtools** | | |
| `fetch_url` | `janito/plugins/tools/local/fetch_url.py` | Web scraping |
| `open_url` | `janito/plugins/tools/local/open_url.py` | Open URLs |
| `open_html_in_browser` | `janito/plugins/tools/local/open_html_in_browser.py` | Open HTML files |
| **dev.pythondev** | | |
| `python_code_run` | `janito/plugins/tools/local/python_code_run.py` | Python execution |
| `python_command_run` | `janito/plugins/tools/local/python_command_run.py` | Python -c execution |
| `python_file_run` | `janito/plugins/tools/local/python_file_run.py` | Python script execution |
| **dev.visualization** | | |
| `read_chart` | `janito/plugins/tools/local/read_chart.py` | Data visualization |
| **core.imagedisplay** | | |
| `show_image` | `janito/plugins/tools/local/show_image.py` | Display single image |
| `show_image_grid` | `janito/plugins/tools/local/show_image_grid.py` | Display multiple images in a grid |
| **ui.userinterface** | | |
| `ask_user` | `janito/plugins/tools/local/ask_user.py` | User interaction |

## Architecture Note

The plugin system in `plugins/` contains **interface definitions and wrappers**, while the actual tool implementations are in `janito/plugins/tools/local/`. 

The real tools are implemented as classes inheriting from `ToolBase` and registered via decorators like `@register_local_tool`.