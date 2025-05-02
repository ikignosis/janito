# delete_text_in_file

Deletes all occurrences of text between a start and end marker (inclusive) in a file, using exact string markers.

## Parameters
- `file_path`: Path to the file to modify.
- `start_marker`: The starting delimiter string.
- `end_marker`: The ending delimiter string.
- `backup`: (optional) If True, create a backup before deleting. Defaults to False.

## Returns
- Status message indicating the result.