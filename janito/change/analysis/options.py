from dataclasses import dataclass, field
from typing import Dict, List
from pathlib import Path
from .models import AnalysisOption


def parse_analysis_options(content: str) -> Dict[str, AnalysisOption]:
    """Parse analysis options from formatted text file"""
    options = {}
    current_option = None
    current_section = None
    
    for line in content.splitlines():
        line = line.strip()
        
        # Skip empty lines and section separators
        if not line or line.startswith('---') or line == 'END_OF_OPTIONS':
            continue
            
        # New option starts with a letter and period
        if line[0].isalpha() and line[1:3] == '. ':
            letter, summary = line.split('. ', 1)
            current_option = AnalysisOption(letter=letter.upper(), summary=summary)
            options[letter.upper()] = current_option
            current_section = None
            continue
            
        # Section headers
        if line.lower() in ['description:', 'action plan:']:
            current_section = 'description'
            continue
        elif line.lower() in ['affected files:', 'modified files:']:
            current_section = 'files'
            continue
            
        # Add items to current section
        if current_option and line.startswith('- '):
            content = line[2:].strip()
            if current_section == 'description':
                current_option.action_plan.append(content)
            elif current_section == 'files':
                current_option.modified_files.append(content)
    
    return options