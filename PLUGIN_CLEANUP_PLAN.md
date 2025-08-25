# Janito Plugin System Cleanup Plan

## Overview
This document outlines the comprehensive cleanup of the janito plugin system to create a unified, maintainable architecture.

## Current Issues Identified

### 1. Redundant Systems
- Multiple plugin loading mechanisms
- Duplicate tool implementations
- Inconsistent plugin discovery

### 2. Directory Structure Problems
- Files scattered across multiple locations
- Unclear separation between core and user plugins
- Legacy files that are no longer used

### 3. Architecture Inconsistencies
- Mixed plugin definition approaches
- Unclear plugin lifecycle management
- Redundant configuration systems

## Cleanup Strategy

### Phase 1: Remove Redundant Systems (Priority: High)

#### Files to Remove
- janito/plugin_system/                    # Entire directory
- janito/plugins/auto_loader.py           # Use manager.py instead
- janito/plugins/auto_loader_fixed.py     # Duplicate
- janito/plugins/discovery_core.py        # Redundant
- janito/plugins/core_adapter.py          # Unused
- janito/plugins/tools/                   # Consolidate into core plugins

#### Files to Consolidate
- Move tools from janito/plugins/tools/ to appropriate core plugins
- Consolidate plugin base classes
- Merge configuration systems

### Phase 2: Restructure Directory Layout

#### New Structure
- janito/plugins/                    # Main plugin system
  - __init__.py
  - manager.py             # Plugin manager
  - discovery.py           # Plugin discovery
  - config.py              # Configuration
  - builtin.py             # Builtin plugins
  - base.py                # Base plugin classes
  - core/                  # Core plugins
    - __init__.py
    - filemanager/       # File operations
    - codeanalyzer/      # Code analysis
    - system/            # System operations
    - imagedisplay/      # Image display
    - dev/               # Development tools
    - ui/                # UI tools
    - web/               # Web tools
  - user/                  # User plugins (empty by default)

### Phase 3: Consolidate Tool Implementations

#### Current Duplications
- janito/plugins/tools/ vs janito/plugins/core/*/tools/
- Multiple implementations of same functionality

#### Consolidation Plan
1. Move all tools to their logical core plugin
2. Remove duplicate implementations
3. Ensure consistent tool interfaces

### Phase 4: Update Plugin Architecture

#### Unified Plugin Definition
Create a standard plugin base class in janito/plugins/base.py

## Implementation Steps

### Step 1: Backup Current State
Create backup of current plugin system

### Step 2: Remove Redundant Files
- Remove old plugin system directory
- Remove duplicate and unused files

### Step 3: Consolidate Tools
Move tools from plugins/tools/ to core plugins

### Step 4: Create New Base Classes
- Create unified plugin base in janito/plugins/base.py
- Ensure compatibility with existing plugins
- Provide clear migration path

### Step 5: Update Configuration
- Consolidate configuration into single system
- Update plugin loading to use new structure
- Ensure backward compatibility

## Testing Strategy

### 1. Unit Tests
- Test each core plugin individually
- Verify tool registration works correctly
- Test plugin loading/unloading

### 2. Integration Tests
- Test plugin system initialization
- Verify all core plugins load correctly
- Test plugin discovery and loading

### 3. Regression Tests
- Ensure existing functionality works
- Verify no tools are lost in consolidation
- Test configuration compatibility

## Migration Timeline

### Week 1: Analysis and Backup
- Complete current system analysis
- Create comprehensive backups
- Plan detailed migration steps

### Week 2: Consolidation
- Remove redundant files
- Consolidate tools into core plugins
- Create new base classes

### Week 3: Testing and Validation
- Comprehensive testing of new system
- Fix any issues discovered
- Update documentation