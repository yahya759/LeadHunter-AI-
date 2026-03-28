from typing import TypedDict


class LeadState(TypedDict):
    industry: str
    location: str
    leads: list
    num_searches: int
    report: str
    error: str
    search_results: list
