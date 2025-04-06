# Project Structure

## Root Files
- `app.py`: Defines the Flask application instance and the main route `/` rendering `index.html`.
- `__main__.py`: Entry point script to run the Flask app, now configured to run in development mode with `debug=True`. Accepts an optional port argument.
- `__init__.py`: (Empty) Marks the directory as a package.

## Folders
- `docs/`: Project documentation.
  - `structure.md`: This file, describing the project structure.
- `templates/`: Contains HTML templates for rendering views.
- `.aurora/`: Internal directory for change history and metadata.

## Behavior
- Running `python -m <module>` or `python __main__.py` will start the Flask app in development mode with debugging enabled.
