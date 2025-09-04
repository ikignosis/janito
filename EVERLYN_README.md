# Everlyn AI PowerShell Integration

This repository contains PowerShell modules and tools for integrating with Everlyn AI - the fastest AI video generation platform in the world.

## Features

- **Fast Video Generation**: Generate AI videos in 15 seconds vs 5 minutes industry standard
- **Cost Effective**: 25x lower cost than competitors
- **Multiple Input Types**: Text-to-video and image-to-video generation
- **PowerShell Integration**: Native PowerShell cmdlets for easy automation
- **Credit Management**: Track and manage your API credits

## Installation

1. Download the `EverlynAI.psm1` and `EverlynAI.psd1` files
2. Place them in your PowerShell modules directory (e.g., `Documents\WindowsPowerShell\Modules\EverlynAI`)
3. Import the module: `Import-Module EverlynAI`

## Quick Start

```powershell
# Connect to Everlyn AI
Connect-EverlynAI -ApiKey "your-api-key-here"

# Check your credits
Get-EverlynAICredits

# Generate a video from text
New-EverlynAIVideo -Prompt "A cat playing in a garden" -Duration 5

# Generate a video from an image
New-EverlynAIVideo -ImagePath "C:\images\cat.jpg" -Prompt "Make the cat dance" -Duration 10
```

## Available Commands

### Connect-EverlynAI
Establishes connection to the Everlyn AI API.

```powershell
Connect-EverlynAI -ApiKey "your-api-key"
```

### Get-EverlynAICredits
Retrieves your current credit balance.

```powershell
Get-EverlynAICredits
```

### New-EverlynAIVideo
Creates a new AI-generated video.

```powershell
# Text to video
New-EverlynAIVideo -Prompt "Your prompt here" -Duration 5

# Image to video
New-EverlynAIVideo -ImagePath "path/to/image.jpg" -Duration 10
```

## API Documentation

### Base URL
```
https://api.everlyn.ai
```

### Authentication
All API requests require an API key passed in the Authorization header:
```
Authorization: Bearer your-api-key
```

### Endpoints

#### GET /v1/credits
Retrieve your current credit balance.

**Response:**
```json
{
  "credits": 100,
  "used": 25,
  "remaining": 75
}
```

#### POST /v1/videos
Create a new video generation request.

**Request Body:**
```json
{
  "type": "text_to_video",
  "prompt": "A cat playing in a garden",
  "duration": 5,
  "model": "default"
}
```

**Response:**
```json
{
  "id": "video-12345",
  "status": "processing",
  "estimated_time": 15
}
```

## Pricing

Everlyn AI offers competitive pricing:

- **Starter**: $9.99/month - 80 credits (~40 videos)
- **Standard**: $34.99/month - 350 credits (~175 videos)
- **Pro**: $94.99/month - 1000 credits (~500 videos)

## Requirements

- PowerShell 5.1 or later
- Windows 10/11 or Windows Server 2016+
- Internet connection for API access

## Support

For support and documentation:
- Website: https://everlyn.ai
- Discord: https://discord.com/invite/DTeDvmeMyT
- Email: support@everlyn.ai

## License

This project is licensed under the MIT License - see the LICENSE file for details.