import os
import sys

# Fix Windows console encoding for Unicode characters
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

load_dotenv()

from graph import build_graph


def main():
    if not os.getenv("OPENROUTER_API_KEY"):
        print("Error: OPENROUTER_API_KEY not set in .env file")
        return
    if not os.getenv("TAVILY_API_KEY"):
        print("Error: TAVILY_API_KEY not set in .env file")
        return

    if len(sys.argv) >= 3:
        job_title = sys.argv[1].strip()
        location = sys.argv[2].strip()
    else:
        job_title = input("Enter job title: ").strip()
        location = input("Enter location: ").strip()

    if not job_title or not location:
        print("Job title and location are required.")
        return

    initial_state = {
        "industry": job_title,
        "job_title": job_title,
        "location": location,
        "leads": [],
        "num_searches": 0,
        "report": "",
        "error": "",
        "search_results": [],
        "seen_linkedin": set(),
    }

    print(f"\nStarting lead research for '{job_title}' in '{location}'...\n")

    app = build_graph()
    final_state = app.invoke(initial_state)

    print("\n" + "=" * 60)
    print(final_state.get("report", "No report generated."))
    print(f"\nLeads saved to leads.csv")


# Expose the graph for API usage
def get_app():
    """Get the compiled graph app for API usage."""
    return build_graph()


if __name__ == "__main__":
    main()
