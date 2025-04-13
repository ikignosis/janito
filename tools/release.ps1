#!/usr/bin/env pwsh
# PowerShell version of the release tool
# Set strict mode to catch errors
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Function to print colored messages
function Print-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Green
}

function Print-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Print-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
    exit 1
}

# Check if hatch is installed
if (-not (Get-Command "hatch" -ErrorAction SilentlyContinue)) {
    Print-Error "hatch is not installed. Please install it first."
}

# Check if twine is installed
if (-not (Get-Command "twine" -ErrorAction SilentlyContinue)) {
    Print-Error "twine is not installed. Please install it first."
}

# Get version from pyproject.toml
if (-not (Test-Path "pyproject.toml")) {
    Print-Error "pyproject.toml not found. Are you running this from the project root?"
}

$ProjectVersionMatch = Select-String -Path "pyproject.toml" -Pattern '^version = "(\d+\.\d+\.\d+)"'
if (-not $ProjectVersionMatch) {
    Print-Error "Could not find version in pyproject.toml"
}
$ProjectVersion = $ProjectVersionMatch.Matches.Groups[1].Value

Print-Info "Project version from pyproject.toml: $ProjectVersion"

# Check PyPI for existing version and compare with latest
Print-Info "Checking PyPI for version information..."
try {
    $PypiInfo = Invoke-RestMethod -Uri "https://pypi.org/pypi/janito/json" -ErrorAction SilentlyContinue
    $LatestVersion = $PypiInfo.info.version
    Print-Info "Latest version on PyPI: $LatestVersion"

    # Check if current version already exists on PyPI
    try {
        $null = Invoke-RestMethod -Uri "https://pypi.org/pypi/janito/$ProjectVersion/json" -ErrorAction SilentlyContinue
        Print-Error "Version $ProjectVersion already exists on PyPI. Please update the version in pyproject.toml."
    } catch {
        # Version doesn't exist on PyPI, which is good
    }

    # Compare versions using proper version comparison
    $ProjectVersionObj = [Version]$ProjectVersion
    $LatestVersionObj = [Version]$LatestVersion

    if ($ProjectVersionObj -lt $LatestVersionObj) {
        Print-Error "Version $ProjectVersion is older than the latest version $LatestVersion on PyPI. Please update the version in pyproject.toml."
    } elseif ($ProjectVersionObj -eq $LatestVersionObj) {
        Print-Error "Version $ProjectVersion is the same as the latest version $LatestVersion on PyPI. Please update the version in pyproject.toml."
    }
} catch {
    Print-Warning "Could not fetch information from PyPI. Will attempt to publish anyway."
}

# Get current git tag
try {
    $CurrentTag = git describe --tags --abbrev=0 2>$null
} catch {
    $CurrentTag = ""
}

if ([string]::IsNullOrEmpty($CurrentTag)) {
    Print-Warning "No git tags found. A new tag will be created during the release process."
    $CurrentTagVersion = ""
} else {
    # Remove 'v' prefix if present
    $CurrentTagVersion = $CurrentTag -replace '^v', ''
    Print-Info "Current git tag: $CurrentTag (version: $CurrentTagVersion)"

    if ($ProjectVersion -ne $CurrentTagVersion) {
        Print-Error "Version mismatch: pyproject.toml ($ProjectVersion) != git tag ($CurrentTagVersion)"
    }

    # Check if the tag points to the current commit
    $CurrentCommit = git rev-parse HEAD
    $TagCommit = git rev-parse "$CurrentTag"
    if ($CurrentCommit -ne $TagCommit) {
        Print-Error "Tag $CurrentTag does not point to the current commit. Please update the tag or create a new one."
    }
}

# Build the package
Print-Info "Removing old dist directory..."
Remove-Item -Recurse -Force dist
Print-Info "Building the package..."
hatch build

# Publish to PyPI
Print-Info "Publishing to PyPI..."
twine upload dist/*

Print-Info "Release process completed successfully."
