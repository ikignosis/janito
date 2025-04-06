# Project Structure

## Root Files

- `app.py`: Flask application instance with a simple route (`/`) returning a greeting. This is the core web app logic.
- `__main__.py`: Entry point script. Parses optional port argument and runs the Flask app on the specified port.
- `index.html`: Landing page styled as a terminal emulator, providing a terminal-like welcome screen for the web app.
- `__init__.py`: Marks the directory as a Python package.

## Bytecode Cache
- `__pycache__/`: Python bytecode cache directory.

## Documentation
- `docs/structure.md`: This file. Describes the purpose and structure of the project files and folders.

## Summary
The project is set up to run a Flask web server. You can start the server by running:

```bash
python -m __main__ [port]
```

which will serve the Flask app on the specified port (default 8000).
