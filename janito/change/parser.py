"""
Parser for AI response to extract operations
"""
from typing import List, Union, Optional
from pathlib import Path
from simple_format_parser.file_operations import CreateFile, DeleteFile, RenameFile
from simple_format_parser.modify_file import ModifyFile

Operation = Union[CreateFile, DeleteFile, RenameFile, ModifyFile]

def parse_response(response: str, preview_dir: Path) -> List[Operation]:
    """Parse AI response into operations between CHANGES_START_HERE and END_OF_CHANGES markers"""
    operations = []

    # Extract content between markers
    start_marker = "CHANGES_START_HERE"
    end_marker = "END_OF_CHANGES"
    
    start_idx = response.find(start_marker)
    if start_idx == -1:
        raise ValueError("Could not find CHANGES_START_HERE marker")
    
    end_idx = response.find(end_marker, start_idx)
    if end_idx == -1:
        raise ValueError("Could not find END_OF_CHANGES marker")
    
    # Extract and parse the changes section
    changes_text = response[start_idx + len(start_marker):end_idx].strip()
    
    # Split into individual operations
    current_operation = []
    for line in changes_text.splitlines():
        if not line.strip() and current_operation:
            # Process completed operation
            op = _create_operation("\n".join(current_operation), preview_dir)
            if op:
                operations.append(op)
            current_operation = []
        else:
            current_operation.append(line)
    
    # Handle last operation if exists
    if current_operation:
        op = _create_operation("\n".join(current_operation), preview_dir)
        if op:
            operations.append(op)

    return operations

def _create_operation(operation_text: str, preview_dir: Path) -> Optional[Operation]:
    """Create an operation from the operation text"""
    lines = operation_text.splitlines()
    if not lines:
        return None

    operation_type = lines[0].strip().lower()
    
    # Parse operation parameters
    params = {}
    content_start = None
    for i, line in enumerate(lines[1:], 1):
        if ':' in line:
            key, value = line.split(':', 1)
            params[key.strip()] = value.strip()
            content_start = i + 1
    
    # Create appropriate operation
    if operation_type == "create file":
        if 'name' in params:
            content = '\n'.join(lines[content_start:])
            return CreateFile(str(preview_dir / params['name']), content)
            
    elif operation_type == "delete file":
        if 'name' in params:
            return DeleteFile(str(preview_dir / params['name']))
            
    elif operation_type == "rename file":
        if 'source' in params and 'target' in params:
            return RenameFile(
                str(preview_dir / params['source']), 
                str(preview_dir / params['target'])
            )
            
    elif operation_type == "modify file":
        if 'name' in params:
            modifier = ModifyFile(str(preview_dir / params['name']))
            
            # Extract contexts and content
            start_context = None
            end_context = None
            new_content = None
            current_section = None
            section_lines = []
            
            for line in lines[content_start:]:
                if line.strip() == 'start_context:':
                    current_section = 'start'
                elif line.strip() == 'end_context:':
                    start_context = '\n'.join(section_lines)
                    section_lines = []
                    current_section = 'end'
                elif line.strip() == 'new_content:':
                    end_context = '\n'.join(section_lines)
                    section_lines = []
                    current_section = 'content'
                elif current_section:
                    section_lines.append(line)
            
            if current_section == 'content':
                new_content = '\n'.join(section_lines)
            
            if start_context and end_context and new_content:
                modifier.ReplaceBlock(start_context, end_context, new_content)
                return modifier
    
    return None