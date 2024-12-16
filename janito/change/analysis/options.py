from dataclasses import dataclass, field
from typing import Dict, List
from pathlib import Path

@dataclass
class AnalysisOption:
    """Represents an analysis option with letter identifier and details"""
    letter: str
    summary: str
    description_items: List[str] = field(default_factory=list)
    affected_files: List[str] = field(default_factory=list)

    def format_option_text(self) -> str:
        """Format option details as text for change core"""
        text = f"Option {self.letter}: {self.summary}\n\n"
        
        if self.description_items:
            text += "Description:\n"
            for item in self.description_items:
                text += f"- {item}\n"
            text += "\n"
            
        if self.affected_files:
            text += "Affected files:\n"
            for file in self.affected_files:
                text += f"- {file}\n"
                
        return text

    def is_new_directory(self, file_path: str) -> bool:
        """Check if file path represents a new directory"""
        parent = str(Path(file_path).parent)
        if parent == '.':
            return False
            
        for other_file in self.affected_files:
            if '(new)' not in other_file and parent in other_file:
                return False
                
        return True

    def get_clean_path(self, file_path: str) -> str:
        """Remove status markers from file path"""
        return file_path.split(' (')[0].strip()

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
        if line.lower() == 'description:':
            current_section = 'description'
            continue
        elif line.lower() == 'affected files:':
            current_section = 'files'
            continue
            
        # Add items to current section
        if current_option and line.startswith('- '):
            content = line[2:].strip()
            if current_section == 'description':
                current_option.description_items.append(content)
            elif current_section == 'files':
                current_option.affected_files.append(content)
    
    return options