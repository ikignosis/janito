import sys
from pathlib import Path
from parser import parse_document, ParserError

def extract_changes(content: str) -> str:
    """Extract content between CHANGES_START_HERE and CHANGES_END_HERE markers."""
    lines = content.splitlines()
    extracted_lines = []
    in_changes_section = False
    
    for line in lines:
        if line.strip() == 'CHANGES_START_HERE':
            in_changes_section = True
            continue
        elif line.strip() == 'CHANGES_END_HERE':
            in_changes_section = False
            continue
        
        if in_changes_section:
            extracted_lines.append(line)
    
    if not extracted_lines:
        return content  # Return original content if markers not found
        
    return '\n'.join(extracted_lines)

def display_statement(statement, indent=0, is_sub=False):
    """Display a statement and its contents with proper indentation."""
    indent_str = "    " * indent
    prefix = "Substatement: " if is_sub else "Statement: "
    print(f"{indent_str}{prefix}{statement.name}")
    
    # Display fields
    if statement.fields:
        print(f"{indent_str}Fields:")
        for key, value in statement.fields.items():
            # Handle multiline values
            value_lines = value.rstrip().split('\n')
            if len(value_lines) == 1:
                print(f"{indent_str}    {key}: {value_lines[0]}")
            else:
                print(f"{indent_str}    {key}:")
                # For multiline fields, preserve the original dot prefix
                for line in value_lines:
                    if line.strip():  # Only add dot for non-empty lines
                        print(f"{indent_str}        .{line}")
                    else:
                        print(f"{indent_str}        {line}")
    
    # Display substatements
    if statement.substatements:
        print(f"{indent_str}Substatements:")
        for substatement in statement.substatements:
            display_statement(substatement, indent + 1, is_sub=True)
            print()  # Add blank line between substatements for better readability

def main():
    if len(sys.argv) != 2:
        print("Usage: python -m parser <input_file>")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    if not input_file.exists():
        print(f"Error: File '{input_file}' does not exist")
        sys.exit(1)
    
    try:
        # Read the file content
        content = input_file.read_text()
        
        # Extract changes section
        changes_content = extract_changes(content)
        
        # Parse the extracted content
        document = parse_document(changes_content)
        
        print(f"Parsed document from {input_file}:")
        print("---")
        for statement in document.statements:
            display_statement(statement)
            print("---")
            
    except ParserError as e:
        print(f"Parser error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 