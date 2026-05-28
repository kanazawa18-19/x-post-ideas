import json
import asyncio
import anthropic
from pathlib import Path
from urllib.parse import quote
from playwright.async_api import async_playwright

COOKIES_PATH = Path(__file__).parent / "cookies.json"
X_TRENDS_URL = "https://x.com/explore/tabs/trending"


async def _scrape_pages(urls_and_labels: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """複数URLをまとめてスクレイピング（ブラウザ1回起動で効率化）"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        cookie_data = json.loads(COOKIES_PATH.read_text())
        await context.add_cookies(cookie_data["cookies"])

        page = await context.new_page()
        results = []

        for url, label in urls_and_labels:
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                await page.wait_for_timeout(3_000)
                if "/login" in page.url:
                    break
                content = await page.inner_text("body")
                results.append((label, content[:2000]))
            except Exception:
                pass

        await browser.close()
        return results


def get_x_trends() -> str:
    results = asyncio.run(_scrape_pages([(X_TRENDS_URL, "trends")]))
    return results[0][1] if results else ""


def get_trending_posts(keywords: list[str]) -> str:
    """X検索のTopタブから主要キーワードのバズ投稿を取得"""
    # 上位3キーワードで検索
    targets = [
        (f"https://x.com/search?q={quote(kw)}&src=typed_query&f=top", kw)
        for kw in keywords[:3]
    ]
    results = asyncio.run(_scrape_pages(targets))
    if not results:
        return ""

    sections = []
    for label, content in results:
        sections.append(f"「{label}」の人気投稿:\n{content[:1200]}")
    return "\n\n".join(sections)


def get_google_trends() -> str:
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl="ja-JP", geo="JP")
        df = pytrends.trending_searches(pn="japan")
        topics = df[0].tolist()[:15]
        return "Googleトレンド（日本）：" + "、".join(topics)
    except Exception:
        return ""


def collect_industry_news(client: anthropic.Anthropic, account: dict) -> str:
    """web_searchで業界・キーワード関連の最新ニュースを取得する"""
    keywords_en = " ".join(account["keywords"][:4])
    keywords_ja = "、".join(account["keywords"][:6])
    prompt = f"""Search "{keywords_en} Japan news 2026" and summarize in Japanese.
Find the latest news and hot topics related to [{keywords_ja}] from the past week.
Output a concise bullet-point list in Japanese. Focus on things timely and relevant for Japanese business professionals."""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if hasattr(block, "text"))


def collect_trends(client: anthropic.Anthropic, account: dict) -> str:
    """XトレンドとGoogleトレンドとバズ投稿と業界ニュースをまとめて返す"""
    sections = []

    x_raw = get_x_trends()
    if x_raw:
        sections.append(f"【Xリアルタイムトレンド】\n{x_raw[:1500]}")

    google = get_google_trends()
    if google:
        sections.append(f"【{google}】")

    trending_posts = get_trending_posts(account["keywords"])
    if trending_posts:
        sections.append(f"【同ジャンルのバズ投稿（参考）】\n{trending_posts}")

    industry = collect_industry_news(client, account)
    if industry:
        sections.append(f"【業界・キーワード関連ニュース】\n{industry}")

    return "\n\n".join(sections) if sections else "（トレンド情報取得できず）"
