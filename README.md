---
title: LeadHunter AI
emoji: 🤖
colorFrom: blue
colorTo: cyan
sdk: docker
pinned: false
---

# LeadHunter AI 🤖

AI-powered lead research agent that finds potential clients by job title and location.

## Features

- 🔍 Intelligent lead search using Tavily API
- 🤖 AI-powered extraction with LLM fallback
- 📧 Contact enrichment
- 📊 Priority scoring
- 📁 CSV export

## Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables in .env
OPENROUTER_API_KEY=your_key
TAVILY_API_KEY=your_key

# Run API server
python api.py

# Or use command line
python main.py "flutter developer" "Saudi Arabia"
```

## API Endpoints

- `POST /search-leads` - Search for leads by job title and location
- `GET /health` - Health check

## Docker

```bash
docker build -t leadhunter-ai .
docker run -p 7860:7860 -e OPENROUTER_API_KEY=your_key -e TAVILY_API_KEY=your_key leadhunter-ai
```
