# LeadHunter AI

An AI-powered lead research agent built with [LangGraph](https://github.com/langchain-ai/langgraph) that automatically discovers, extracts, and enriches company contact information from the web.

## Features

- **Automated Company Discovery** — Searches the web for companies in any industry and location using Tavily
- **AI-Powered Data Extraction** — Uses LLMs via OpenRouter to extract structured lead data from search results
- **Contact Enrichment** — Automatically enriches leads with email, phone, website, and description by searching for each company individually
- **Model Rotation & Fallback** — Cycles through multiple free LLM models with automatic failover on rate limits
- **CSV Export** — Saves all leads to a structured `leads.csv` file

## Architecture

```
search_node → extract_node → [conditional] → enrich_node → report_node
```

| Node | Description |
|------|-------------|
| `search_node` | Queries Tavily for companies (max 10 results per search) |
| `extract_node` | Sends results to LLM to extract structured company data |
| `enrich_node` | Searches each company individually for contact details |
| `report_node` | Generates report and saves leads to CSV |

**Conditional routing** after `extract_node`:
- If leads ≥ 10 → proceed to `enrich_node`
- If searches ≥ 2 → proceed to `enrich_node`
- Otherwise → loop back to `search_node`

## Project Structure

```
lead_research_agent/
├── main.py          # Entry point
├── state.py         # State definition (LeadState TypedDict)
├── nodes.py         # All node implementations
├── graph.py         # Graph builder with conditional edges
├── utils.py         # LLM client and Tavily client helpers
├── requirements.txt # Python dependencies
├── .gitignore
└── .env.example     # Environment variable template
```

## Installation

### Prerequisites

- Python 3.10+
- [OpenRouter](https://openrouter.ai/) API key
- [Tavily](https://tavily.com/) API key

### Setup

```bash
# Clone the repository
git clone https://github.com/yahya759/LeadHunter-AI-.git
cd LeadHunter-AI-/lead_research_agent

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env and add your API keys
```

### Environment Variables

Create a `.env` file in the `lead_research_agent/` directory:

```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
```

## Usage

### Interactive Mode

```bash
python main.py
```

You will be prompted to enter an industry and location.

### Command-Line Arguments

```bash
python main.py "Software" "Cairo, Egypt"
```

### Example Output

```
Starting lead research for 'Software' in 'Cairo, Egypt'...

[Search] Searching for: Software companies in Cairo, Egypt
[Search] Found 10 results
[Extract] Extracting leads from 10 search results
[Extract] Added 61 new leads (total: 61)
[Enrich] Enriching 61 leads with contact details...
[Report] Generating report for 61 leads
[Report] Saved leads.csv
```

## Supported LLM Models

The agent rotates through these free models on [OpenRouter](https://openrouter.ai/) with automatic fallback on rate limits:

| Model |
|-------|
| stepfun/step-3.5-flash:free |
| nvidia/nemotron-3-super-120b-a12b:free |
| arcee-ai/trinity-large-preview:free |
| z-ai/glm-4.5-air:free |
| nvidia/nemotron-3-nano-30b-a3b:free |
| arcee-ai/trinity-mini:free |
| nvidia/nemotron-nano-9b-v2:free |
| nvidia/nemotron-nano-12b-v2-vl:free |
| minimax/minimax-m2.5:free |

## Dependencies

- `langgraph` — Graph-based AI agent framework
- `langchain-openai` — OpenAI-compatible LLM integration
- `langchain-community` — Community integrations
- `tavily-python` — Web search API client
- `python-dotenv` — Environment variable management
- `pandas` — CSV export

## License

MIT
