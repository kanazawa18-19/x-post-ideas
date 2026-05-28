import re
import json
import asyncio
import anthropic
from pathlib import Path
from urllib.parse import quote
from playwright.async_api import async_playwright

COOKIES_PATH = Path(__file__).parent / "cookies.json"
X_TRENDS_URL = "https://x.com/explore/tabs/trending"


async def _scrape_pages(urls_and_labels: list[tuple[str, str]]) -> list[tuple[str, str]]:
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


def _extract_trend_names(raw: str) -> list[str]:
    """Xトレンドの生テキストからトレンド名を抽出する"""
    lines = raw.split("\n")
    names = []
    for i, line in enumerate(lines):
        if "トレンド" in line and "·" in line and i + 1 < len(lines):
            name = lines[i + 1].strip()
            if name and len(name) < 30 and not name.isdigit() and name not in names:
                names.append(name)
    return names[:10]


def get_x_trends() -> tuple[str, list[str]]:
    """(生テキスト, トレンド名リスト)を返す"""
    results = asyncio.run(_scrape_pages([(X_TRENDS_URL, "trends")]))
    if not results:
        return "", []
    raw = results[0][1]
    return raw, _extract_trend_names(raw)


def get_trending_posts(keywords: list[str]) -> tuple[str, list[str]]:
    """(生テキスト, 検索したキーワードリスト)を返す"""
    kws = keywords[:3]
    targets = [
        (f"https://x.com/search?q={quote(kw)}&src=typed_query&f=top", kw)
        for kw in kws
    ]
    results = asyncio.run(_scrape_pages(targets))
    if not results:
        return "", []

    sections = []
    for label, content in results:
        sections.append(f"「{label}」の人気投稿:\n{content[:1200]}")
    return "\n\n".join(sections), kws


def get_google_trends() -> tuple[list[str], str]:
    """(トレンド名リスト, 表示用文字列)を返す"""
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl="ja-JP", geo="JP")
        df = pytrends.trending_searches(pn="japan")
        topics = df[0].tolist()[:15]
        return topics, "、".join(topics)
    except Exception:
        return [], ""


def collect_industry_news(client: anthropic.Anthropic, account: dict) -> str:
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


def collect_precedents(client: anthropic.Anthropic, account: dict) -> str:
    """世の中の前例・ノウハウ・成功失敗事例を収集する"""
    keywords_ja = "、".join(account["keywords"][:5])
    prompt = f"""「{keywords_ja}」に関連する以下を日本語で調査してください：
- 実際の成功事例・失敗事例（企業名や具体的な話があると尚良い）
- 知っておくべき定番ノウハウ・ベストプラクティス
- 「これは使える」「意外と知られていない」系の知見

投稿ネタとして使えそうなものを箇条書きで5〜8個まとめてください。"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if hasattr(block, "text"))


def collect_x_calendar(client: anthropic.Anthropic, account: dict) -> str:
    """今日の記念日・業界イベント・季節ネタを収集する"""
    from datetime import date
    today = date.today()
    date_str = today.strftime("%Y年%m月%d日")
    keywords_ja = "、".join(account["keywords"][:4])

    prompt = f"""今日（{date_str}）に関連する以下を日本語で調査してください：
1. 今日の記念日・何の日（一般的なもの）
2. 今週・今月の「{keywords_ja}」に関連する業界イベント・啓発週間・法令施行日など
3. 季節的に今の時期に刺さるネタ（時季性のある話題）

投稿に絡めやすいものを箇条書きで3〜5個まとめてください。"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if hasattr(block, "text"))


def collect_x_algorithm(client: anthropic.Anthropic) -> str:
    """Xの最新アルゴリズムの傾向を取得する"""
    prompt = """Search "X Twitter algorithm 2025 2026 how to grow reach engagement" and summarize in Japanese.
Find the latest information on:
- What types of posts X algorithm currently favors
- Best practices for reach and follower growth
- What to avoid (shadowban, reduced reach)
- Any recent algorithm changes

Output a concise bullet-point list in Japanese."""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if hasattr(block, "text"))


def collect_trends(client: anthropic.Anthropic, account: dict) -> dict:
    """
    Returns:
        content: Claudeに渡す全文
        sources: Slackに表示する参考情報の箇条書き
    """
    content_sections = []
    source_lines = []

    x_raw, x_names = get_x_trends()
    if x_raw:
        content_sections.append(f"【Xリアルタイムトレンド】\n{x_raw[:1500]}")
        if x_names:
            source_lines.append(f"• Xトレンド：{' / '.join(x_names[:8])}")

    google_list, google_str = get_google_trends()
    if google_str:
        content_sections.append(f"【Googleトレンド（日本）】\n{google_str}")
        source_lines.append(f"• Googleトレンド：{' / '.join(google_list[:5])}")

    buzz_text, buzz_kws = get_trending_posts(account["keywords"])
    if buzz_text:
        content_sections.append(f"【同ジャンルのバズ投稿（参考）】\n{buzz_text}")
        source_lines.append(f"• バズ投稿参照：「{'」「'.join(buzz_kws)}」の人気投稿")

    industry = collect_industry_news(client, account)
    if industry:
        content_sections.append(f"【業界・キーワード関連ニュース】\n{industry}")
        source_lines.append("• 業界ニュース：最新情報をweb検索で参照")

    precedents = collect_precedents(client, account)
    if precedents:
        content_sections.append(f"【前例・ノウハウ・事例】\n{precedents}")
        source_lines.append("• 前例・ノウハウ：成功失敗事例・ベストプラクティスを参照")

    calendar = collect_x_calendar(client, account)
    if calendar:
        content_sections.append(f"【Xカレンダー（今日の記念日・季節ネタ）】\n{calendar}")
        source_lines.append("• Xカレンダー：今日の記念日・業界イベント・季節ネタを参照")

    algorithm = collect_x_algorithm(client)
    if algorithm:
        content_sections.append(f"【Xの最新アルゴリズム傾向】\n{algorithm}")
        source_lines.append("• Xアルゴリズム：最新の拡散・リーチ傾向を参照")

    return {
        "content": "\n\n".join(content_sections) or "（トレンド情報取得できず）",
        "sources": "\n".join(source_lines) if source_lines else "（情報取得できず）",
    }
