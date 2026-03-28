import os
import itertools

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import SecretStr


load_dotenv()

MODELS = [
    "stepfun/step-3.5-flash:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "arcee-ai/trinity-large-preview:free",
    "z-ai/glm-4.5-air:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "arcee-ai/trinity-mini:free",
    "nvidia/nemotron-nano-9b-v2:free",
    "nvidia/nemotron-nano-12b-v2-vl:free",
    "minimax/minimax-m2.5:free",
]

_model_cycle = itertools.cycle(MODELS)


def get_llm(model: str | None = None):
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    selected = model if model else next(_model_cycle)
    return ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=SecretStr(api_key),
        model=selected,
        temperature=0,
    )


def get_llm_with_fallback(prompt_messages, max_retries: int | None = None):
    if max_retries is None:
        max_retries = len(MODELS)

    last_error = None
    for attempt in range(max_retries):
        model = next(_model_cycle)
        try:
            llm = get_llm(model=model)
            response = llm.invoke(prompt_messages)
            return response, model
        except Exception as e:
            last_error = e
            err_str = str(e)
            if "429" in err_str or "rate" in err_str.lower():
                print(f"  [LLM] {model} rate-limited, trying next model...")
                continue
            else:
                print(f"  [LLM] {model} error: {e}")
                continue

    raise Exception(f"All models failed. Last error: {last_error}")


def get_tavily_client():
    from tavily import TavilyClient

    return TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
