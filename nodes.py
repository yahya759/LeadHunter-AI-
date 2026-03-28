import json
import re
from langchain_core.messages import HumanMessage
from state import LeadState
from utils import get_llm_with_fallback, get_tavily_client


def search_node(state: LeadState) -> dict:
    print(f"[Search] Searching for: {state['industry']} companies in {state['location']}")

    search_variants = [
        f"{state['industry']} companies in {state['location']}",
        f"top {state['industry']} businesses {state['location']}",
    ]

    variant_idx = state.get("num_searches", 0)
    query = search_variants[variant_idx % len(search_variants)]

    try:
        client = get_tavily_client()
        response = client.search(query=query, search_depth="advanced", max_results=10)
        results = response.get("results", [])
        print(f"[Search] Found {len(results)} results")
        return {"num_searches": state.get("num_searches", 0) + 1, "search_results": results}
    except Exception as e:
        print(f"[Search] Error: {e}")
        return {"num_searches": state.get("num_searches", 0) + 1, "error": f"Search failed: {e}", "search_results": []}


def extract_node(state: LeadState) -> dict:
    results = state.get("search_results", [])
    if not results:
        print("[Extract] No results to extract from")
        return {"leads": state.get("leads", [])}

    print(f"[Extract] Extracting leads from {len(results)} search results")

    results_text = "\n---\n".join(
        f"Title: {r.get('title', 'N/A')}\nURL: {r.get('url', 'N/A')}\nContent: {r.get('content', 'N/A')}"
        for r in results
    )

    prompt = f"""Extract ALL company leads from these search results about {state['industry']} companies in {state['location']}.

Rules:
- If the URL is a company website, use it as the website field
- Extract any email, phone, description found in content
- Use content snippet as description if available

Return ONLY a valid JSON array. Example:
[{{"company_name": "Acme Corp", "website": "https://acme.com", "email": "info@acme.com", "phone": "+1234567890", "description": "Software company"}}]

Search Results:
{results_text}"""

    try:
        response, used_model = get_llm_with_fallback([HumanMessage(content=prompt)])
        print(f"  [Extract] LLM model used: {used_model}")
        content = response.content.strip()

        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content.rsplit("```", 1)[0]

        new_leads = json.loads(content)
        if not isinstance(new_leads, list):
            new_leads = []

        existing = state.get("leads", [])
        seen = {l.get("company_name", "").lower() for l in existing}
        added = 0
        for lead in new_leads:
            name = (lead.get("company_name") or "").lower()
            if name and name not in seen:
                seen.add(name)
                existing.append(lead)
                added += 1

        print(f"[Extract] Added {added} new leads (total: {len(existing)})")
        return {"leads": existing}
    except Exception as e:
        print(f"[Extract] Error: {e}")
        return {"leads": state.get("leads", []), "error": f"Extraction failed: {e}"}


def enrich_node(state: LeadState) -> dict:
    leads = state.get("leads", [])
    if not leads:
        return {}

    location = state.get("location", "")
    print(f"[Enrich] Enriching {len(leads)} leads with contact details...")
    client = get_tavily_client()

    for i, lead in enumerate(leads):
        name = lead.get("company_name", "")
        if not name:
            continue

        try:
            query = f"{name} email phone contact {location}"
            response = client.search(query=query, search_depth="basic", max_results=3)

            combined = ""
            for r in response.get("results", []):
                combined += r.get("url", "") + " " + r.get("content", "") + "\n"

            if not lead.get("website"):
                for r in response.get("results", []):
                    url = r.get("url", "")
                    if url and name.lower().replace(" ", "").split(".")[0] in url.lower().replace(" ", ""):
                        lead["website"] = url
                        break

            if not lead.get("email"):
                emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", combined)
                if emails:
                    lead["email"] = emails[0]

            if not lead.get("phone"):
                phones = re.findall(r"\+?[\d][\d\s\-().]{6,18}", combined)
                for p in phones:
                    digits = re.sub(r"\D", "", p)
                    if len(digits) >= 7:
                        lead["phone"] = p.strip()
                        break

            if not lead.get("description"):
                for r in response.get("results", []):
                    content = r.get("content", "")
                    if content and len(content) > 30:
                        lead["description"] = content[:300]
                        break

            print(f"  [Enrich] {i+1}/{len(leads)} {name}: email={lead.get('email', '-')}, phone={lead.get('phone', '-')}, website={lead.get('website', '-')}")
        except Exception as e:
            print(f"  [Enrich] Error enriching {name}: {e}")

    return {"leads": leads}


def report_node(state: LeadState) -> dict:
    leads = state.get("leads", [])
    print(f"[Report] Generating report for {len(leads)} leads")

    if not leads:
        return {"report": "No leads found."}

    try:
        import pandas as pd

        df = pd.DataFrame(leads)
        for col in ["company_name", "website", "email", "phone", "description"]:
            if col not in df.columns:
                df[col] = None
        df = df[["company_name", "website", "email", "phone", "description"]]
        df.to_csv("leads.csv", index=False)
        print("[Report] Saved leads.csv")
    except Exception as e:
        print(f"[Report] CSV save error: {e}")

    report_lines = [f"Lead Research Report: {state['industry']} in {state['location']}", "=" * 60, ""]
    for i, lead in enumerate(leads, 1):
        report_lines.append(f"{i}. {lead.get('company_name', 'Unknown')}")
        if lead.get("website"):
            report_lines.append(f"   Website: {lead['website']}")
        if lead.get("email"):
            report_lines.append(f"   Email: {lead['email']}")
        if lead.get("phone"):
            report_lines.append(f"   Phone: {lead['phone']}")
        if lead.get("description"):
            report_lines.append(f"   Description: {lead['description']}")
        report_lines.append("")

    report = "\n".join(report_lines)
    return {"report": report}
