"""Options handling for analysis module."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Tuple
import re

@dataclass
class AnalysisOption:
    letter: str
    summary: str
    affected_files: List[str]
    description_items: List[str]

    def get_clean_path(self, file_path: str) -> str:
        """Get clean path without markers"""
        return file_path.split(' (')[0].strip()
        
    def is_new_file(self, file_path: str) -> bool:
        """Check if file is marked as new"""
        return '(new)' in file_path
        
    def is_removed_file(self, file_path: str) -> bool:
        """Check if file is marked as removed"""
        return '(removed)' in file_path

    def get_affected_paths(self, workdir: Path = None) -> List[Path]:
        """Get list of affected paths, resolving against workdir if provided"""
        paths = []
        for file_path in self.affected_files:
            clean_path = self.get_clean_path(file_path)
            path = workdir / clean_path if workdir else Path(clean_path)
            paths.append(path)
        return paths

    def process_file_path(self, path: str) -> Tuple[str, bool, bool]:
        """Process a file path to extract clean path and modification flags
        Returns: (clean_path, is_new, is_modified)
        """
        clean_path = path.strip()
        is_new = False
        is_modified = False
        
        if "(new)" in clean_path:
            is_new = True
            clean_path = clean_path.replace("(new)", "").strip()
        if "(modified)" in clean_path:
            is_modified = True
            clean_path = clean_path.replace("(modified)", "").strip()
            
        return clean_path, is_new, is_modified

def parse_analysis_options(response: str) -> Dict[str, AnalysisOption]:
    """Parse options from the response text."""
    options = {}
    
    if 'END_OF_OPTIONS' in response:
        response = response.split('END_OF_OPTIONS')[0]
    
    current_option = None
    current_section = None
    
    lines = response.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        option_match = re.match(r'^([A-Z])\.\s+(.+)$', line)
        if option_match:
            if current_option:
                options[current_option.letter] = current_option
                
            letter, summary = option_match.groups()
            current_option = AnalysisOption(
                letter=letter,
                summary=summary,
                affected_files=[],
                description_items=[]
            )
            current_section = None
            continue
            
        if re.match(r'^-+$', line):
            continue
        
        if current_option:
            if line.lower() == 'description:':
                current_section = 'description'
                continue
            elif line.lower() == 'affected files:':
                current_section = 'files'
                continue
            
            if line.startswith('- '):
                content = line[2:].strip()
                if current_section == 'description':
                    current_option.description_items.append(content)
                elif current_section == 'files':
                    if '(new)' in content or '(modified)' in content:
                        current_option.affected_files.append(content)
    
    if current_option:
        options[current_option.letter] = current_option
    
    return options
