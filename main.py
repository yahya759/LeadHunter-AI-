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
        industry = sys.argv[1].strip()
        location = sys.argv[2].strip()
    else:
        industry = input("Enter industry: ").strip()
        location = input("Enter location: ").strip()

    if not industry or not location:
        print("Industry and location are required.")
        return

    initial_state = {
        "industry": industry,
        "location": location,
        "leads": [],
        "num_searches": 0,
        "report": "",
        "error": "",
        "search_results": [],
    }

    print(f"\nStarting lead research for '{industry}' in '{location}'...\n")

    app = build_graph()
    final_state = app.invoke(initial_state)

    print("\n" + "=" * 60)
    print(final_state.get("report", "No report generated."))
    print(f"\nLeads saved to leads.csv")


if __name__ == "__main__":
    main()
