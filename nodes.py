import json
import re
from langchain_core.messages import HumanMessage
from state import LeadState
from utils import get_llm_with_fallback, get_tavily_client


def clean_phone(phone):
    """Clean and validate phone number."""
    if not phone:
        return ""
    phone_str = str(phone).strip()
    digits_only = re.sub(r'\D', '', phone_str)
    if len(digits_only) < 7 or len(digits_only) > 13:
        return ""
    return phone_str


def calculate_priority(lead):
    """Calculate priority score for a lead."""
    score = 0
    if lead.get("linkedin"):
        score += 3
    if lead.get("email"):
        score += 2
    if lead.get("phone") and len(lead["phone"]) >= 7:
        score += 2
    if lead.get("company_name"):
        score += 2
    if lead.get("website"):
        score += 1
    return min(score, 10)


def search_node(state: LeadState) -> dict:
    job_title = state.get("job_title", "")
    location = state.get("location", "")
    
    # Boolean search queries for finding clients who NEED the service
    search_variants = [
        f'("hiring" OR "looking for" OR "need") "{job_title}" {location} site:linkedin.com',
        f'"{job_title}" "{location}" (freelancer OR contractor OR remote) LinkedIn',
        f'CEO OR founder OR CTO "{location}" "{job_title}" project contact',
        f'company "{location}" looking for "{job_title}" developer startup',
        f'"need" OR "wanted" OR "required" "{job_title}" {location} project',
    ]
    
    variant_idx = state.get("num_searches", 0)
    query = search_variants[variant_idx % len(search_variants)]
    
    print(f"[Search] Query {variant_idx + 1}: {query}")

    try:
        client = get_tavily_client()
        response = client.search(query=query, search_depth="advanced", max_results=10)
        results = response.get("results", [])
        print(f"[Search] Found {len(results)} results")
        return {
            "num_searches": state.get("num_searches", 0) + 1, 
            "search_results": results,
            "location": location
        }
    except Exception as e:
        print(f"[Search] Error: {e}")
        return {"num_searches": state.get("num_searches", 0) + 1, "error": f"Search failed: {e}", "search_results": []}


def extract_node(state: LeadState) -> dict:
    results = state.get("search_results", [])
    if not results:
        print("[Extract] No results to extract from")
        return {"leads": state.get("leads", [])}

    print(f"[Extract] Extracting leads from {len(results)} search results")
    
    job_title = state.get("job_title", "freelancer")
    location = state.get("location", "unknown")

    results_text = "\n---\n".join(
        f"Title: {r.get('title', 'N/A')}\nURL: {r.get('url', 'N/A')}\nContent: {r.get('content', 'N/A')}"
        for r in results
    )

    prompt = f"""Extract BUSINESS OWNERS who are LOOKING FOR {job_title} in {location}.

Your task: Find people who NEED this service, NOT people who have this skill.

Look for:
- Business owners who posted about needing {job_title}
- Companies hiring for {job_title} role
- Startups looking for {job_title} freelancers
- CTOs/founders seeking {job_title} for their projects

Rules:
- Extract LinkedIn profile URLs of the person seeking the skill (look for linkedin.com/in/ in URLs or content)
- Extract person name (the person seeking help, not the freelancer)
- Extract company/organization name if available
- Identify their profession/title (CEO, founder, CTO, manager, etc.)
- Identify location/country from content
- Extract phone/WhatsApp (prefer format: +966, +971, +962, +20, +1, etc.)
- Extract email if available
- Extract website if available

Return ONLY a valid JSON array. Example:
[{{"owner_name": "Sarah Ahmed", "company_name": "Tech Startup KSA", "industry": "tech startup", "country": "{location}", "linkedin": "https://linkedin.com/in/sarahahmed", "phone": "+966501234567", "email": "sarah@techstartup.com", "website": "https://techstartup.com"}}]

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
        seen_linkedin = state.get("seen_linkedin", set())
        added = 0
        for lead in new_leads:
            # Clean and validate phone
            lead["phone"] = clean_phone(lead.get("phone", ""))
            
            # Deduplication by LinkedIn URL
            linkedin = lead.get("linkedin", "")
            if linkedin and linkedin in seen_linkedin:
                continue
            if linkedin:
                seen_linkedin.add(linkedin)
            
            # Ensure all required fields exist
            for field in ["owner_name", "company_name", "industry", "country", "linkedin", "phone", "email", "website"]:
                if field not in lead:
                    lead[field] = None
            existing.append(lead)
            added += 1

        print(f"[Extract] Added {added} new leads (total: {len(existing)})")
        return {"leads": existing, "seen_linkedin": seen_linkedin}
    except Exception as e:
        print(f"[Extract] Error: {e}")
        return {"leads": state.get("leads", []), "error": f"Extraction failed: {e}"}


def enrich_node(state: LeadState) -> dict:
    leads = state.get("leads", [])
    if not leads:
        return {}

    job_title = state.get("job_title", "freelancer")
    location = state.get("location", "unknown")
    
    print(f"[Enrich] Enriching {len(leads)} leads with contact details and identifying pain points...")
    client = get_tavily_client()

    for i, lead in enumerate(leads):
        owner_name = lead.get("owner_name", "")
        company_name = lead.get("company_name", "")
        industry = lead.get("industry", "")
        
        search_name = owner_name or company_name
        if not search_name:
            continue

        try:
            # Search for LinkedIn and contact info
            query = f'"{search_name}" LinkedIn profile WhatsApp contact'
            response = client.search(query=query, search_depth="basic", max_results=5)

            combined = ""
            for r in response.get("results", []):
                combined += r.get("url", "") + " " + r.get("content", "") + "\n"
                url = r.get("url", "")
                # Extract LinkedIn if not already present
                if not lead.get("linkedin") and "linkedin.com/in/" in url.lower():
                    lead["linkedin"] = url

            # Enrich phone/WhatsApp with strict validation
            if not lead.get("phone"):
                # Look for WhatsApp patterns first
                whatsapp_pattern = r'\+?(9[0-9][0-9])\s?[0-9]{7,8}'
                whatsapp_phones = re.findall(whatsapp_pattern, combined)
                for match in whatsapp_phones:
                    phone = "+" + match
                    if clean_phone(phone):
                        lead["phone"] = clean_phone(phone)
                        break
                
                # Fallback to any phone
                if not lead.get("phone"):
                    phones = re.findall(r"\+?[\d][\d\s\-().]{6,18}", combined)
                    for p in phones:
                        cleaned = clean_phone(p)
                        if cleaned:
                            lead["phone"] = cleaned
                            break
            
            # Apply strict phone validation
            lead["phone"] = clean_phone(lead.get("phone", ""))

            # Enrich email
            if not lead.get("email"):
                emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", combined)
                for email in emails:
                    if "example" not in email.lower() and "test" not in email.lower():
                        lead["email"] = email
                        break

            # Enrich website
            if not lead.get("website"):
                for r in response.get("results", []):
                    url = r.get("url", "")
                    if url and not "linkedin" in url.lower() and not "facebook" in url.lower():
                        lead["website"] = url
                        break

            print(f"  [Enrich] {i+1}/{len(leads)} {search_name}: linkedin={lead.get('linkedin', '-')[:50] if lead.get('linkedin') else '-'}..., phone={lead.get('phone', '-')}")
        except Exception as e:
            print(f"  [Enrich] Error enriching {search_name}: {e}")

    return {"leads": leads}


def report_node(state: LeadState) -> dict:
    leads = state.get("leads", [])
    print(f"[Report] Generating report for {len(leads)} leads")

    if not leads:
        return {"report": "No leads found."}

    job_title = state.get("job_title", "freelancer")
    location = state.get("location", "unknown")
    
    # Industry-specific pain points for personalized outreach
    industry_pain_points = {
        "recruitment": "توفير وقت فريقك في فلترة المرشحين",
        "software development": "تسريع دورة تطوير المنتج",
        "software": "تسريع دورة تطوير المنتج",
        "development": "تسريع دورة تطوير المنتج",
        "holding company": "أتمتة التقارير والعمليات الداخلية",
        "investment": "أتمتة التقارير والعمليات الداخلية",
        "IT": "تقليل التكرار في المهام التقنية",
        "technology": "تقليل التكرار في المهام التقنية",
        "restaurant": "إدارة الطلبات والتوصيل بكفاءة",
        "food": "إدارة الطلبات والتوصيل بكفاءة",
        "salon": "إدارة الحجوزات والعملاء بشكل احترافي",
        "clinic": "تحسين تجربة المرضى وتذكيرهم بالمواعيد",
        "store": "إدارة المخزون والمبيعات بكفاءة",
        "ecommerce": "إدارة المتجر والمخزون بكفاءة",
        "agency": "إدارة المشاريع والعملاء بكفاءة",
        "marketing": "تحسين حملات التسويق الرقمي",
        "consulting": "أتمتة التواصل مع العملاء",
        "real estate": "إدارة العقارات والعملاء بكفاءة",
        "education": "إدارة الطلاب والدورات التعليمية",
        "healthcare": "تحسين رعاية المرضى",
        "finance": "أتمتة التقارير المالية",
        "logistics": "تحسين إدارة الشحن والتوصيل",
        "construction": "إدارة المشاريع والموردين",
        "retail": "تحسين تجربة العملاء والمبيعات",
    }
    
    for lead in leads:
        owner_name = lead.get("owner_name", "") or "فريقكم"
        company_name = lead.get("company_name", "") or ""
        industry = lead.get("industry", "").lower()
        
        # Find matching pain point
        pain_point = "تحسين العمليات وادارة الموارد"
        for key, value in industry_pain_points.items():
            if key in industry:
                pain_point = value
                break
        
        # Generate personalized outreach message in Arabic
        if company_name:
            lead["outreach_message"] = f"مرحباً {owner_name}\n\nتشرفنا بالتواصل مع {company_name}. {pain_point} من اولوياتكم في المجال.\n\nانا {job_title} متخصص — عندك 15 دقيقة نتحدث؟"
        else:
            lead["outreach_message"] = f"مرحباً {owner_name}\n\n{pain_point} من اولوياتكم في المجال. بتشرفني نتواصل.\n\nانا {job_title} متخصص — عندك 15 دقيقة؟"
        
        # Calculate priority score using the function
        lead["priority_score"] = calculate_priority(lead)

    # Sort by priority score descending
    leads_sorted = sorted(leads, key=lambda x: x.get("priority_score", 0), reverse=True)

    # Save to CSV
    try:
        import pandas as pd

        df = pd.DataFrame(leads_sorted)
        columns = ["priority_score", "owner_name", "company_name", "industry", "country", 
                   "linkedin", "phone", "email", "website", "outreach_message"]
        for col in columns:
            if col not in df.columns:
                df[col] = None
        df = df[columns]
        df.to_csv("leads.csv", index=False)
        print("[Report] Saved leads.csv (sorted by priority)")
    except Exception as e:
        print(f"[Report] CSV save error: {e}")

    # Generate text report
    report_lines = [f"تقرير بحث العملاء: {job_title} في {location}", "=" * 60, ""]
    for i, lead in enumerate(leads_sorted, 1):
        score = lead.get("priority_score", 0)
        report_lines.append(f"{i}. {lead.get('owner_name', 'Unknown')} ({lead.get('company_name', '-')})")
        report_lines.append(f"   الصناعة: {lead.get('industry', '-')} | الدولة: {lead.get('country', '-')}")
        report_lines.append(f"   اولوية: {score}/10")
        if lead.get("linkedin"):
            report_lines.append(f"   LinkedIn: {lead['linkedin']}")
        if lead.get("phone"):
            report_lines.append(f"   هاتف: {lead['phone']}")
        if lead.get("email"):
            report_lines.append(f"   ايميل: {lead['email']}")
        if lead.get("outreach_message"):
            report_lines.append(f"   رسالة التواصل: {lead['outreach_message'][:100]}...")
        report_lines.append("")

    report = "\n".join(report_lines)
    return {"report": report}
