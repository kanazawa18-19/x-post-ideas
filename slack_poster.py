from slack_sdk import WebClient


def post_to_thread(client: WebClient, channel_id: str, thread_ts: str, text: str) -> None:
    client.chat_postMessage(
        channel=channel_id,
        thread_ts=thread_ts,
        text=text,
    )
