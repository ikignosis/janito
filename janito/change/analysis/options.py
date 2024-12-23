from dataclasses import dataclass, field
from typing import Dict, List
from pathlib import Path

@dataclass
class AnalysisOption:
    """Represents an analysis option with letter identifier and action plan"""
    letter: str
    summary: str
    action_plan: List[str] = field(default_factory=list)
    modified_files: List[str] = field(default_factory=list)

    def add_action_item(self, item: str) -> None:
        """Add an action plan item, cleaning up any formatting"""
        cleaned = item.strip('- ').strip()
        if cleaned:
            self.action_plan.append(cleaned)

    def format_option_text(self) -> str:
        """Format option details as text for change core"""
        text = f"Option {self.letter} - {self.summary}\n"
        text += "=" * len(f"Option {self.letter} - {self.summary}") + "\n\n"
        
        if self.action_plan:
            text += "Description:\n"
            for item in self.action_plan:
                text += f"- {item}\n"
            text += "\n"
            
        if self.modified_files:
            text += "Modified files:\n"
            for file in self.modified_files:
                text += f"- {file}\n"
                
        return text

    def is_new_directory(self, file_path: str) -> bool:
        """Check if file path represents the first occurrence of a directory"""
        parent = str(Path(file_path).parent)
        return parent != '.' and not any(
            parent in self.get_clean_path(file)
            for file in self.modified_files
            if self.get_clean_path(file) != file_path
        )

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