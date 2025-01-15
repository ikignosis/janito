# File Operations
Modify File
name: file_name
# Should support the follow substatements:

# Replace old lines with new lines
- Replace
  old_lines: 
    .line1
    .line2
  new_lines:
    .line3
    .line4

# Delete sequence of lines matching "old_lines"
- Delete
  old_lines:
    .line1
    .line2

# Add sequence of "new_lines" after "current_lines"
# If current_lines is not specified, adds to end of file
- Add
  current_lines: # Optional - if not specified, adds to end of file
    .line1
    .line2
  new_lines:
    .line1
    .line2

