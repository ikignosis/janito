# File Operations
Modify File

# Should support the follow substatements:

1. Identify the content that should be affected by the change:
- Select Between
# Selects lines between start_lines and end_lines
	start_lines:
        .line1
        .line2
	end_lines:
        .line3
        .line4
- Select Over:
# Select lines between and including start_lines and end_lines
	start_lines:
        .line1
        .line2
	end_lines:
        .line3
        .line4
- Select Exact:
# Select lines matching the exact content
	content:
        .line1

# A Select operation must be followed by one of the following operations
- Delete # Deletes the selected lines
- Replace # Replaces the selected lines with the new content
    new_content:
        .line1
        .line2
- Insert # Inserts the new content before the selected lines
    new_content:
        .line1
        .line2
- Append # Appends the new content after the selected lines
    new_content:
        .line1
        .line2

