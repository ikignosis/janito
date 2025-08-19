# Plugin Resources Overview

## Introduction

This document details the resources provided by each built-in plugin in the Janito system. Plugins contribute various capabilities to extend the functionality of the core system, organized by functional domains.

## Resource Types

Plugins primarily provide **tools** that enable specific operations. Each tool is a self-contained function that performs a particular task, with defined inputs, outputs, and security permissions.

## Plugin Resource Summary

### File Manager Plugin (`core.filemanager`)

Provides essential file and directory operations:

- **File Operations**: create, read, update, delete files
- **Directory Management**: create, remove directories (recursive)
- **File Search**: find files by pattern, respecting .gitignore
- **Text Replacement**: find and replace text in files
- **Syntax Validation**: validate syntax of various file types

### Code Analyzer Plugin (`core.codeanalyzer`)

Provides code structure analysis and searching:

- **File Outlining**: extract classes, functions, methods from files
- **Outline Searching**: search for structural elements in code
- **Text Searching**: full-text search across files with regex support

### System Tools Plugin (`core.system`)

Provides system-level operations:

- **Command Execution**: run PowerShell commands on Windows

### Web Tools Plugin (`web.webtools`)

Provides web interaction capabilities:

- **Web Scraping**: fetch content from URLs
- **Browser Integration**: open URLs and HTML files in default browser

### Python Development Plugin (`dev.pythondev`)

Provides Python execution tools:

- **Code Execution**: run Python code via stdin
- **Command Execution**: execute Python with -c flag
- **Script Running**: execute Python script files

### Visualization Plugin (`dev.visualization`)

Provides data visualization:

- **Chart Rendering**: display bar, line, pie charts and tables in terminal

### User Interface Plugin (`ui.userinterface`)

Provides user interaction:

- **User Input**: prompt users for input and clarification

## Resource Contribution

Each plugin contributes resources that enable specific workflows:

- **File Manager**: enables code editing, project organization, and file manipulation
- **Code Analyzer**: supports code navigation, refactoring, and understanding
- **System Tools**: allows system administration and environment inspection
- **Web Tools**: facilitates research, documentation, and online data collection
- **Python Development**: supports development, testing, and automation
- **Visualization**: enhances data analysis and reporting
- **User Interface**: enables interactive, human-guided workflows

These resources work together to create a comprehensive development environment that combines AI assistance with powerful tooling.