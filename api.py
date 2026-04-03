import asyncio
import os
import sys
from concurrent.futures import ThreadPoolExecutor

# Fix Windows console encoding for Unicode characters
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from graph import build_graph

# Load environment variables from .env file
load_dotenv()

# Check for required API keys
if not os.getenv("OPENROUTER_API_KEY"):
    raise RuntimeError("OPENROUTER_API_KEY not set in .env file")
if not os.getenv("TAVILY_API_KEY"):
    raise RuntimeError("TAVILY_API_KEY not set in .env file")

# Global app instance
graph = build_graph()
executor = ThreadPoolExecutor(max_workers=3)


class SearchRequest(BaseModel):
    job_title: str
    location: str
    max_leads: Optional[int] = 20


class SearchResponse(BaseModel):
    leads: list
    total: int
    status: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the graph on startup."""
    print("Initializing LeadHunter AI graph...")
    print("Graph initialized successfully!")
    yield
    print("Shutting down...")


app = FastAPI(
    title="LeadHunter AI API",
    description="API for finding and researching leads by job title and location",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


def run_graph(request):
    """Run the graph in a background thread."""
    return graph.invoke({
        "job_title": request.job_title,
        "location": request.location,
        "max_leads": request.max_leads,
        "leads": [],
        "search_queries": [],
        "search_results": [],
        "num_searches": 0,
        "seen_linkedin": set(),
    })


@app.post("/search-leads", response_model=SearchResponse)
async def search_leads(request: SearchRequest):
    """
    Search for leads by job title and location.
    
    - **job_title**: The job title to search for (e.g., "motion designer", "developer")
    - **location**: The location/country to search in (e.g., "Saudi Arabia", "UAE")
    - **max_leads**: Maximum number of leads to return (default: 20)
    """
    try:
        print(f"\n[API] Searching for '{request.job_title}' in '{request.location}'...")
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(executor, run_graph, request)
        leads = result.get("leads", [])
        
        print(f"[API] Found {len(leads)} leads")
        
        return SearchResponse(
            leads=leads,
            total=len(leads),
            status="success"
        )
        
    except Exception as e:
        print(f"[API] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860, timeout_keep_alive=300)
