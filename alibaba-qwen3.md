# Alibaba Cloud Qwen Models Overview

## Flagship Models (Singapore Region)

| Model        | Description                                    | Max Context Window | Input Price (per million tokens) | Output Price (per million tokens) |
|--------------|------------------------------------------------|--------------------|----------------------------------|-----------------------------------|
| Qwen-Max     | Ideal for complex tasks, most powerful         | 32,768             | $1.6                             | $6.4                              |
| Qwen-Plus    | Balanced performance, speed, and cost          | 1,000,000          | $0.4                             | $1.2                              |
| Qwen-Flash   | Ideal for simple tasks, fast and low-cost      | 1,000,000          | $0.05                            | $0.4                              |
| Qwen-Coder   | Excellent code model, excels at tool calling   | 1,000,000          | $0.3                             | $1.5                              |

## Model Categories

### Text Generation - Qwen
Commercial models:
- QwQ
- Qwen-Max
- Qwen-Plus
- Qwen-Flash

Open-source models:
- Qwen3
- Qwen2.5

Multimodal models:
- Qwen-VL (visual understanding)
- QVQ (visual reasoning)
- Qwen-Omni (omni-modal)
- Qwen-Omni-Realtime (real-time multimodal)

Domain-specific models:
- Code model
- Translation model
- Role-play model

### Image Generation - Qwen
- Qwen-Image: Text-to-image, excels at rendering complex text (Chinese/English)
- Qwen-Image-Edit: Image and text editing operations (style transfer, text modification, object editing)
- Wan: Generates exquisite images from a single sentence

### Video Generation
- Text-to-video: Generates videos from a single sentence
- Image-to-video:
  - First-frame-to-video
  - First-and-last-frame-to-video
  - Multi-image-to-video

### Video Editing
- General-purpose video editing: Performs various video editing tasks based on text, images, and videos

### Embedding
- Text embedding: Converts text into numbers for search, clustering, recommendation, and classification tasks

## Qwen-Max Details

### Qwen3-Max (Preview)
- Context window: 262,144 tokens
- Maximum input: 258,048 tokens
- Maximum output: 65,536 tokens
- Input pricing (tiered):
  - 0-32K tokens: $1.2 per million tokens
  - 32K-128K tokens: $2.4 per million tokens
  - 128K-252K tokens: $3 per million tokens
- Output price: $6 per million tokens
- Free quota: 1 million tokens (validity: 90 days after activating Alibaba Cloud Model Studio)
- Supports context cache

### Qwen-Max (Stable/Latest)
- Context window: 32,768 tokens
- Maximum input: 30,720 tokens
- Maximum output: 8,192 tokens
- Input price: $1.6 per million tokens
- Output price: $6.4 per million tokens
- 50% discount for batch calling
- Free quota: 1 million tokens each for input and output (validity: 90 days after activating Alibaba Cloud Model Studio)

### Qwen-Max Snapshots
- qwen-max-2025-01-25 (also known as qwen-max-0125, Qwen2.5-Max)

## Qwen-Plus
This model provides balanced capabilities between Qwen-Max and Qwen-Flash, making it ideal for moderately complex tasks.