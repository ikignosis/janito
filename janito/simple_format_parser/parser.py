from dataclasses import dataclass
from typing import List, Dict, Optional
import re

@dataclass
class Statement:
    name: str
    fields: Dict[str, str]
    substatements: List['Statement']

@dataclass
class Document:
    statements: List[Statement]

class ParserError(Exception):
    pass

class Parser:
    def __init__(self, content: str):
        self.lines = content.splitlines()
        self.current_line = 0
        self.current_indent = 0

    def parse(self) -> Document:
        statements = []
        while self.current_line < len(self.lines):
            line = self._current_line_stripped()
            if not line or line.startswith('#'):
                self.current_line += 1
                continue
            if line.startswith('==='):
                self.current_line += 1
                continue
            
            statement = self._parse_statement()
            if statement:
                statements.append(statement)
                
        return Document(statements=statements)

    def _current_line_stripped(self) -> str:
        if self.current_line >= len(self.lines):
            return ''
        return self.lines[self.current_line].strip()

    def _get_indent(self, line: str) -> int:
        return len(line) - len(line.lstrip())

    def _parse_statement(self) -> Optional[Statement]:
        line = self._current_line_stripped()
        if not line or line.startswith('#'):
            return None

        # Don't treat lines starting with '.' as statements
        if line.startswith('.'):
            return None

        name = line.split('#')[0].strip()
        self.current_line += 1

        fields = {}
        substatements = []

        while self.current_line < len(self.lines):
            line = self.lines[self.current_line]
            stripped = line.strip()

            if not stripped or stripped.startswith('#'):
                self.current_line += 1
                continue
            
            if stripped.startswith('==='):
                self.current_line += 1
                break

            if stripped.startswith('-'):
                substatement = self._parse_substatement()
                if substatement:
                    substatements.append(substatement)
                continue

            if ':' in line:
                key, value = self._parse_field()
                fields[key] = value
                continue

            # Don't break on lines starting with '.' - they're part of multiline fields
            if not stripped.startswith('.'):
                break

            self.current_line += 1

        return Statement(name=name, fields=fields, substatements=substatements)

    def _parse_substatement(self) -> Optional[Statement]:
        line = self._current_line_stripped()
        if not line.startswith('-'):
            return None

        name = line[1:].split('#')[0].strip()
        self.current_line += 1
        
        fields = {}
        while self.current_line < len(self.lines):
            line = self.lines[self.current_line]
            stripped = line.strip()
            
            if not stripped or stripped.startswith('#'):
                self.current_line += 1
                continue

            indent = self._get_indent(line)
            if indent == 0 or stripped.startswith('==='):
                break

            if ':' in line:
                key, value = self._parse_field()
                fields[key] = value
                continue

            # Don't break on lines starting with '.' - they're part of multiline fields
            if not stripped.startswith('.'):
                break

            self.current_line += 1

        return Statement(name=name, fields=fields, substatements=[])

    def _parse_field(self) -> tuple[str, str]:
        line = self.lines[self.current_line]
        key, rest = [x.strip() for x in line.split(':', 1)]
        
        # Handle comments after the colon
        rest = rest.split('#')[0].strip()
        
        self.current_line += 1
        
        # If there's content after the colon, it's a single-line field
        if rest:
            return key, rest
            
        # Otherwise, it's a multi-line field
        content_lines = []
        while self.current_line < len(self.lines):
            line = self.lines[self.current_line]
            stripped = line.strip()
            
            if not stripped:
                self.current_line += 1
                continue
            
            if stripped.startswith('#'):
                self.current_line += 1
                continue
            
            if not stripped.startswith('.'):
                break
            
            content_lines.append(stripped[1:])
            self.current_line += 1
            
        return key, '\n'.join(content_lines) + '\n'

def parse_document(content: str) -> Document:
    return Parser(content).parse()
