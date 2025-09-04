@{
    RootModule = 'EverlynAI.psm1'
    ModuleVersion = '1.0.0'
    GUID = '12345678-1234-1234-1234-123456789012'
    Author = 'Your Name'
    CompanyName = 'Your Company'
    Copyright = '(c) 2025 Your Company. All rights reserved.'
    Description = 'PowerShell module for interacting with Everlyn AI API'
    PowerShellVersion = '5.1'
    FunctionsToExport = @('Connect-EverlynAI', 'Get-EverlynAICredits', 'New-EverlynAIVideo')
    CmdletsToExport = @()
    VariablesToExport = @()
    AliasesToExport = @()
    PrivateData = @{
        PSData = @{
            Tags = @('AI', 'Video', 'Image', 'Generation', 'Everlyn')
            LicenseUri = ''
            ProjectUri = ''
            ReleaseNotes = 'Initial release of Everlyn AI PowerShell module'
        }
    }
}