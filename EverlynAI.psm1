# Everlyn AI PowerShell Module
$Script:EverlynBaseUrl = "https://api.everlyn.ai"
$Script:ApiKey = $null
$Script:DefaultHeaders = @{"Content-Type" = "application/json"; "User-Agent" = "EverlynAI-PowerShell/1.0"}
function Connect-EverlynAI { param([Parameter(Mandatory=$true)][string]$ApiKey); $Script:ApiKey = $ApiKey; $Script:DefaultHeaders["Authorization"] = "Bearer $ApiKey"; Write-Host "Connected to Everlyn AI API" -ForegroundColor Green }
function Get-EverlynAICredits { if (-not $Script:ApiKey) { throw "Not connected to Everlyn AI. Use Connect-EverlynAI first." }; try { $response = Invoke-RestMethod -Uri "$Script:EverlynBaseUrl/v1/credits" -Headers $Script:DefaultHeaders -Method Get; return $response } catch { throw "Failed to get credits: $_" } }
function New-EverlynAIVideo { param([Parameter(Mandatory=$true)][string]$Prompt, [int]$Duration = 5); if (-not $Script:ApiKey) { throw "Not connected to Everlyn AI. Use Connect-EverlynAI first." }; Write-Host "Video generation: $Prompt (Duration: ${Duration}s)" }
