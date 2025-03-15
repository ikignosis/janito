"""
Test script for the str_replace_editor tool.
This script tests all the commands implemented in the text editor tool.
"""
import os
import sys
import pathlib

# Add the parent directory to sys.path to import janito modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from janito.tools.str_replace_editor import str_replace_editor

def print_separator(title):
    """Print a separator with a title."""
    print("\n" + "=" * 50)
    print(f" {title} ".center(50, "="))
    print("=" * 50 + "\n")

def main():
    """Test all text editor commands."""
    # Test file path
    test_file = "test_editor_file.py"
    
    # Clean up any existing test file
    if os.path.exists(test_file):
        os.remove(test_file)
    
    # 1. Test create command
    print_separator("Testing CREATE command")
    create_result = str_replace_editor(
        command="create",
        path=test_file,
        file_text="def hello():\n    print('Hello, World!')\n\nif __name__ == '__main__':\n    hello()\n"
    )
    print(f"Create result: {create_result}")
    
    # 2. Test view command
    print_separator("Testing VIEW command")
    view_result = str_replace_editor(
        command="view",
        path=test_file
    )
    print(f"View result: {view_result}")
    
    # 3. Test view command with range
    print_separator("Testing VIEW command with range")
    view_range_result = str_replace_editor(
        command="view",
        path=test_file,
        view_range=[1, 2]
    )
    print(f"View with range result: {view_range_result}")
    
    # 4. Test str_replace command
    print_separator("Testing STR_REPLACE command")
    str_replace_result = str_replace_editor(
        command="str_replace",
        path=test_file,
        old_str="Hello, World!",
        new_str="Hello from the text editor tool!"
    )
    print(f"String replace result: {str_replace_result}")
    
    # View file after str_replace
    view_after_replace = str_replace_editor(
        command="view",
        path=test_file
    )
    print(f"File after replace: {view_after_replace['content']}")
    
    # 5. Test insert command
    print_separator("Testing INSERT command")
    insert_result = str_replace_editor(
        command="insert",
        path=test_file,
        insert_line=0,
        new_str="# Test file for the text editor tool\n"
    )
    print(f"Insert result: {insert_result}")
    
    # View file after insert
    view_after_insert = str_replace_editor(
        command="view",
        path=test_file
    )
    print(f"File after insert: {view_after_insert['content']}")
    
    # 6. Test undo_edit command
    print_separator("Testing UNDO_EDIT command")
    undo_result = str_replace_editor(
        command="undo_edit",
        path=test_file
    )
    print(f"Undo result: {undo_result}")
    
    # View file after undo
    view_after_undo = str_replace_editor(
        command="view",
        path=test_file
    )
    print(f"File after undo: {view_after_undo['content']}")
    
    # 7. Test another undo_edit command
    print_separator("Testing second UNDO_EDIT command")
    undo_result2 = str_replace_editor(
        command="undo_edit",
        path=test_file
    )
    print(f"Second undo result: {undo_result2}")
    
    # View file after second undo
    view_after_undo2 = str_replace_editor(
        command="view",
        path=test_file
    )
    print(f"File after second undo: {view_after_undo2['content']}")
    
    # 8. Test error handling
    print_separator("Testing ERROR handling")
    
    # Test missing path
    missing_path_result = str_replace_editor(
        command="view"
    )
    print(f"Missing path result: {missing_path_result}")
    
    # Test non-existent file
    non_existent_file_result = str_replace_editor(
        command="view",
        path="non_existent_file.py"
    )
    print(f"Non-existent file result: {non_existent_file_result}")
    
    # Test missing parameters for str_replace
    missing_params_result = str_replace_editor(
        command="str_replace",
        path=test_file
    )
    print(f"Missing parameters result: {missing_params_result}")
    
    # Clean up
    if os.path.exists(test_file):
        os.remove(test_file)
    
    print_separator("All tests completed")

if __name__ == "__main__":
    main()
