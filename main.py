import os
from datetime import datetime, timezone, timedelta

import anthropic
from slack_sdk import WebClient

from config import ACCOUNTS, CHANNEL_ID, SPREADSHEET_ID, CREDENTIALS_PATH
from trend_collector import collect_trends, collect_shared_context
from analytics_reader import get_top_posts
from idea_generator import generate_ideas
from slack_poster import post_to_thread

JST = timezone(timedelta(hours=9))
DIVIDER = "─" * 24


def build_message(account: dict, now: datetime, sources: str, ideas: str) -> str:
    time_str = now.strftime("%Y/%m/%d %H:%M")
    return f"""\
📅 *{account["name"]}さんの投稿ネタ｜{time_str}*

*📊 参考にした情報*
{sources}

{DIVIDER}

{ideas.strip()}"""


def main() -> None:
    now = datetime.now(JST)
    anthropic_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    slack_client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])

    # 全アカウント共通の情報を1回だけ取得
    print("共通コンテキスト取得中（アルゴリズム・記念日）...")
    shared_ctx = collect_shared_context(anthropic_client)

    for account in ACCOUNTS:
        name = account["name"]
        print(f"--- {name}さんの処理開始 ---")

        print("  トレンド収集中...")
        trend_data = collect_trends(anthropic_client, account, shared_context=shared_ctx)

        print("  過去投稿データ取得中...")
        try:
            past_posts = get_top_posts(SPREADSHEET_ID, account["sheet_tweet"], CREDENTIALS_PATH)
        except Exception as e:
            print(f"  過去データ取得エラー（スキップ）: {e}")
            past_posts = ""

        print("  ネタ生成中...")
        ideas = generate_ideas(anthropic_client, account, trend_data, past_posts)

        message = build_message(account, now, trend_data["sources"], ideas)
        post_to_thread(
            client=slack_client,
            channel_id=CHANNEL_ID,
            thread_ts=account["thread_ts"],
            text=message,
        )
        print(f"  ✓ Slackに投稿しました")


if __name__ == "__main__":
    main()
