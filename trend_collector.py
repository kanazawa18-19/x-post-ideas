import re
import json
import time
import random
import asyncio
import anthropic
from pathlib import Path
from urllib.parse import quote
from playwright.async_api import async_playwright

COOKIES_PATH = Path(__file__).parent / "cookies.json"
X_TRENDS_URL = "https://x.com/explore/tabs/trending"
_API_INTERVAL = 15  # API呼び出し間隔（秒）


def _web_search(client: anthropic.Anthropic, prompt: str, max_tokens: int = 600) -> str:
    """web_searchツール付きClaude呼び出し。429エラー時は60秒待ってリトライ。"""
    for attempt in range(3):
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=max_tokens,
                tools=[{"type": "web_search_20250305", "name": "web_search"}],
                messages=[{"role": "user", "content": prompt}],
            )
            return "".join(block.text for block in response.content if hasattr(block, "text"))
        except anthropic.RateLimitError:
            if attempt == 2:
                return ""
            print(f"  レートリミット到達、60秒待機してリトライ ({attempt + 1}/3)...")
            time.sleep(60)
    return ""


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
    kws = random.sample(keywords, min(3, len(keywords)))
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


def collect_shared_context(client: anthropic.Anthropic) -> str:
    """全アカウント共通：Xアルゴリズム + 今日の記念日を1回で取得"""
    from datetime import date
    today = date.today()
    date_str = today.strftime("%Y年%m月%d日")
    prompt = f"""以下の2点を日本語で調査してください：

1. Search "X Twitter algorithm 2025 2026 reach engagement tips" — Xの最新アルゴリズムで伸びる投稿の特徴を箇条書き5点で
2. 今日（{date_str}）の記念日・何の日 — 投稿に使えそうなものを箇条書き3点で"""
    return _web_search(client, prompt, max_tokens=600)


def collect_account_context(client: anthropic.Anthropic, account: dict) -> str:
    """アカウントごと：業界ニュース + 前例ノウハウを1回で取得"""
    sampled = random.sample(account["keywords"], min(6, len(account["keywords"])))
    keywords_en = " ".join(sampled[:4])
    keywords_ja = "、".join(sampled)
    prompt = f"""以下の2点を日本語で調査してください：

1. Search "{keywords_en} Japan news 2026" — 「{keywords_ja}」に関連する直近1週間の最新ニュース・話題を箇条書き5点で
2. 「{keywords_ja}」の成功失敗事例・定番ノウハウ・意外と知られていない知見を箇条書き5点で"""
    return _web_search(client, prompt, max_tokens=800)


def collect_trends(client: anthropic.Anthropic, account: dict, shared_context: str = "") -> dict:
    """
    shared_context: 全アカウント共通の情報（アルゴリズム+記念日）。初回のみ取得して使い回す。
    Returns:
        buzz_posts: 同ジャンルのバズ投稿
        industry_news: 業界ニュース・前例ノウハウ
        algorithm_tips: Xアルゴリズム・今日の記念日
        x_trends: Xリアルタイムトレンド
        google_trends: Googleトレンド
        sources: Slackに表示する参考情報の箇条書き
    """
    source_lines = []

    x_raw, x_names = get_x_trends()
    x_trends = x_raw[:1500] if x_raw else ""
    if x_names:
        source_lines.append(f"• Xトレンド：{' / '.join(x_names[:8])}")

    google_list, google_str = get_google_trends()
    google_trends = google_str if google_str else ""
    if google_str:
        source_lines.append(f"• Googleトレンド：{' / '.join(google_list[:5])}")

    buzz_text, buzz_kws = get_trending_posts(account["keywords"])
    buzz_posts = buzz_text if buzz_text else ""
    if buzz_text:
        source_lines.append(f"• バズ投稿参照：「{'」「'.join(buzz_kws)}」の人気投稿")

    industry_news = collect_account_context(client, account)
    if industry_news:
        source_lines.append("• 業界ニュース・前例ノウハウ：web検索で参照")

    algorithm_tips = shared_context if shared_context else ""
    if shared_context:
        source_lines.append("• Xアルゴリズム・今日の記念日：web検索で参照")

    return {
        "buzz_posts": buzz_posts,
        "industry_news": industry_news,
        "algorithm_tips": algorithm_tips,
        "x_trends": x_trends,
        "google_trends": google_trends,
        "sources": "\n".join(source_lines) if source_lines else "（情報取得できず）",
    }
