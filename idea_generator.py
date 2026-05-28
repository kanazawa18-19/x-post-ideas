import anthropic
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))

_TIME_CONTEXT = {
    7:  "朝（通勤・起床直後のユーザーが多い。前向き・モチベーション系や役立つTipsが刺さる）",
    12: "昼（休憩中のユーザーが多い。さっと読める短めコンテンツや共感系が効果的）",
    19: "夕方（退勤後のユーザーが多い。一日の振り返りや明日に役立つ情報が好まれる）",
    22: "夜（ゆっくり読みたいユーザーが多い。少し深い内容や思考を促すコンテンツが刺さる）",
}

_PROMPT = """\
あなたはX（Twitter）の投稿コンサルタントです。
以下の情報を踏まえて、今投稿するXの下書きを10案作成してください。

【ペルソナ】
{persona}

【コンテンツの柱（どれかをテーマに選ぶ）】
{pillars}

【今日のXトレンド・業界動向】
{trends}

{past_posts}

【今の時間帯】
{time_context}

【出力形式】
①〜⑩の番号をつけて、以下の形式で出力してください：

（投稿文）
・ポイント1
・ポイント2

投稿文の条件：
- 280文字以内
- 改行を使って読みやすく
- 一人称は「私」
- 友人に話すようなカジュアルなトーン。ですます調より「〜だよ」「〜だった」「〜と思う」「〜なんだけど」などの口語体
- 専門用語は使ってOKだが、固くなりすぎない
- 過去の投稿・同ジャンルのバズ投稿がある場合はその言い回し・トーン・構成を参考にする
- トレンドや業界動向を自然に組み込む

ポイントの条件：
- なぜこの投稿が伸びるか、何が刺さるかを箇条書き2〜3行で
- ハッシュタグ・長い解説は不要

バズりやすい要素：具体的数字・意外性・あるある共感・個人の体験談・リスト形式
"""


def generate_ideas(client: anthropic.Anthropic, account: dict, trends: str, past_posts: str) -> str:
    hour = datetime.now(JST).hour
    closest = min(_TIME_CONTEXT, key=lambda h: abs(h - hour))

    prompt = _PROMPT.format(
        persona=account["persona"],
        pillars="\n".join(f"- {p}" for p in account["pillars"]),
        trends=trends or "（取得できませんでした）",
        past_posts=past_posts or "",
        time_context=_TIME_CONTEXT[closest],
    )

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text
