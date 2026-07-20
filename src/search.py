from duckduckgo_search import DDGS

def get_live_news_context(sport_name):
    """
    Searches the live web for recent sport news, matches, or events.
    Returns a unified text summary of search snippets.
    """
    search_query = f"{sport_name} latest tournament results championship winners news 2026"
    retrieved_texts = []

    print(f"[INFO]: Executing web search for: '{search_query}'...")
    try:
        # Instantiate DDGS client and execute text query
        with DDGS() as ddgs:
            results = ddgs.text(search_query, max_results=3)
            
            # If search succeeds but returns empty
            if not results:
                return "No recent search engine updates found. Continuing using offline historical database only."

            for index, r in enumerate(results, start=1):
                title = r.get("title", "No Title")
                snippet = r.get("body", "No Snippet Content Available")
                url = r.get("href", "#")
                retrieved_texts.append(f"Web Source {index}: {title} ({url})\nSnippet: {snippet}")

    except Exception as e:
        print(f"[ERROR]: Web Search fell back or failed: {e}")
        return f"No recent search engine updates available due to system connectivity issue: {str(e)}"

    return "\n\n".join(retrieved_texts)
