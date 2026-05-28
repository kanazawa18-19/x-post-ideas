import os
from datetime import datetime, timezone, timedelta

import anthropic
from slack_sdk import WebClient

from config import ACCOUNTS, CHANNEL_ID, SPREADSHEET_ID, CREDENTIALS_PATH
from trend_collector import collect_trends
from analytics_reader import get_top_posts
from idea_generator import generate_ideas
from slack_poster import post_to_thread

JST = timezone(timedelta(hours=9))


def main() -> None:
    now = datetime.now(JST)
    anthropic_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    slack_client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])

    for account in ACCOUNTS:
        name = account["name"]
        print(f"--- {name}さんの処理開始 ---")

        print("  トレンド収集中...")
        trends = collect_trends(anthropic_client, account)

        print("  過去投稿データ取得中...")
        try:
            past_posts = get_top_posts(SPREADSHEET_ID, account["sheet_tweet"], CREDENTIALS_PATH)
        except Exception as e:
            print(f"  過去データ取得エラー（スキップ）: {e}")
            past_posts = ""

        print("  ネタ生成中...")
        ideas = generate_ideas(anthropic_client, account, trends, past_posts)

        time_str = now.strftime("%Y/%m/%d %H:%M")
        message = f"📅 *{time_str} の投稿ネタ — {name}さん*\n\n{ideas.strip()}"
        post_to_thread(
            client=slack_client,
            channel_id=CHANNEL_ID,
            thread_ts=account["thread_ts"],
            text=message,
        )
        print(f"  ✓ Slackに投稿しました")


if __name__ == "__main__":
    main()
