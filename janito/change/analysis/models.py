from dataclasses import dataclass, field
from typing import List
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

    @property
    def action_plan_text(self) -> str:
        """Format action plan as text for change core"""
        items = [f"- {item}" for item in self.action_plan]
        return "\n".join(items)

    def get_files_by_status(self, status: str) -> List[str]:
        """Get files filtered by their status marker.
        
        Args:
            status: Status to filter by ('new', 'modified', or 'removed')
        
        Returns:
            List of file paths with the specified status
        """
        return [
            self.get_clean_path(file) 
            for file in self.modified_files 
            if f"({status})" in file
        ]
