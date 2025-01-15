This is a simple line based format, it supports


1. comments: # in any part of a line
Note: Do not strip comments beforehand as they might be part of a muilline literal (see 3.1)

2. statements: one or more words; preferably a verb and a noun (eg. Create File)
3. key/values after statements or substatement (see 4.) 
3.1 in sing line fields: key: value
3.1 multi line fields:
key: # The values in the following lines will be collected literally, preserving identation and special characters
.line1
# comments between literal lines must be ignored (not breaking the literal sequence)
.  line2
Note: all the lines will be stripped of the leading dot and concatenated with "\n", the last line will also have a "\n" appended

Important: Fields must be properly indented to be associated with their statement or substatement.
For statements, fields start at the same indentation level as the statement.
For substatements (starting with -), fields must be indented one level more than the substatement.

Example:

Change File
path: test.txt  # statement field (no indent)
- Replace Block # substatement
    old: abc    # substatement field (indented)
new: xyz        # statement field (no indent)

4. Substatements as list items after the statement or it's fields
Example:

Change File # Statement
path: test.txt  # field
- Replacement # This is a substatement
    field1: value1 # single line field
    field2: # multi line field
.line1
.line2
# the above field2 will have the value "line1\nline2\n"

5. Statments must finish with a line starting with "=", empty lines are ignored

7. Examples:

Create File
name: myfile.txt
content:
.line1
.line2
.line3
===

Delete File
name: myfile.txt
===

Modify File
name: myfile.txt
- Replace Block
  # Replace all lines between start_context and end_context with new_content
  start_context:
  .line1
  end_context:
  .line6
  new_content:
  .line7
  .line8
===

8. Implementation Guidelines
- the parser should return a document object with a .statements property that is a list of statement objects
- the statement objects should have a .name, .fields and .substatements properties (all optional)
- raise errors for invalid statements, fields and substatements 
