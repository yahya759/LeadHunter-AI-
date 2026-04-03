from typing import TypedDict, Set


class LeadState(TypedDict):
    industry: str
    job_title: str
    location: str
    leads: list
    num_searches: int
    report: str
    error: str
    search_results: list
    target_countries: list
    seen_linkedin: Set[str]
