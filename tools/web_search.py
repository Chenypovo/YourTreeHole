from core.tools import tool


@tool(name="web_search", description="搜索网页获取信息")
def web_search(query: str) -> str:
    """Search the web for information. Returns search result snippets."""
    import urllib.request
    import urllib.parse
    import json

    url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MyAgent/0.1"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        results = []
        if data.get("AbstractText"):
            results.append(data["AbstractText"])
        for topic in data.get("RelatedTopics", [])[:5]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append(topic["Text"])

        return "\n".join(results) if results else "未找到相关结果。"
    except Exception as e:
        return f"搜索失败: {e}"
