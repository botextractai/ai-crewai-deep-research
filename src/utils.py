import os
from dotenv import load_dotenv, find_dotenv

# expects to find a .env file at the directory above
def load_env():
    _ = load_dotenv(find_dotenv())

def get_openai_api_key():
    load_env()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    return openai_api_key

def get_exa_api_key():
    load_env()
    exa_api_key = os.getenv("EXA_API_KEY")
    return exa_api_key

def get_exa_base_url():
    load_env()
    exa_base_url = os.getenv("EXA_BASE_URL")
    return exa_base_url

def get_scrape_max_chars():
    load_env()
    scrape_max_chars = os.getenv("SCRAPE_MAX_CHARS")
    return int(scrape_max_chars)

def get_research_async_enabled():
    load_env()
    raw_value = os.getenv("RESEARCH_ASYNC_ENABLED", "false")
    return raw_value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
