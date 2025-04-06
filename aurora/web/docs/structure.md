# Project Structure

## Root Files
- `app.py`: Defines the Flask application.
  - `/`: Serves the web interface.
  - `/execute_stream`: POST endpoint that accepts user input and streams the Aurora agent's response back to the client using server-sent events (SSE).
- `__main__.py`: Entry point script to run the Flask app, configured to run in development mode with `debug=True`. Accepts an optional port argument.
- `__init__.py`: (Empty) Marks the directory as a package.

## Folders
- `docs/`: Project documentation.
  - `structure.md`: This file, describing the project structure.
- `templates/`: Contains HTML templates for rendering views.
  - `index.html`: Terminal-style web interface. Accepts user input, sends commands to backend, and displays output dynamically.
- `.aurora/`: Internal directory for change history and metadata.

## Behavior
- Running `python -m <module>` or `python __main__.py` will start the Flask app in development mode with debugging enabled.
- The web interface allows entering shell commands, which are sent to the backend.
- The backend uses the Aurora agent to process the commands and streams the response back to the frontend via SSE.
