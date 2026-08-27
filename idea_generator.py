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

━━━━━━━━━━━━━━━━━━━━━━
■ 最優先：同ジャンルのバズ投稿
━━━━━━━━━━━━━━━━━━━━━━
{buzz_posts}
→ 切り口・構成・問いかけ方を参考に、必ず2〜3案はこれを起点として作ること。内容のコピーは不要、「こういうアングルが刺さる」という発想を借りる。

━━━━━━━━━━━━━━━━━━━━━━
■ 参考：業界ニュース・ノウハウ
━━━━━━━━━━━━━━━━━━━━━━
{industry_news}
→ タイムリーな話題をネタの入口として活用する。

━━━━━━━━━━━━━━━━━━━━━━
■ 文体参考：過去の高パフォーマンス投稿
━━━━━━━━━━━━━━━━━━━━━━
{past_posts}
→ 内容ではなく、言い回し・使う言葉・ニュアンス・トーンを真似ること。この人らしい書き方・口癖・テンションを全案に反映する。

━━━━━━━━━━━━━━━━━━━━━━
■ 補助：Xアルゴリズム・今日の記念日
━━━━━━━━━━━━━━━━━━━━━━
{algorithm_tips}
→ 投稿形式の参考や時事フックとして補助的に使う。

━━━━━━━━━━━━━━━━━━━━━━
■ 参考程度：Xトレンド・Googleトレンド
━━━━━━━━━━━━━━━━━━━━━━
{x_trends}
{google_trends}
→ 関連するものがあれば自然に組み込む。無理に使わない。

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
- トレンドや業界動向を自然に組み込む

ポイントの条件：
- なぜこの投稿が伸びるか、何が刺さるかを箇条書き2〜3行で
- ハッシュタグ・長い解説は不要

Xアルゴリズムに沿った書き方：
- 本文に外部リンクを入れない（リーチが下がる。URLは返信欄に誘導する）
- 冒頭1〜2行でスクロールを止める（最初の一文が命）
- 返信したくなる問いかけや意見を入れる（返信数がアルゴリズムに強い）
- 保存したくなる情報密度（ブックマークはアルゴリズムへの強いシグナル）
- 画像・動画は添付できる内容だとなお良い（テキストのみより有利）
- トレンドワードを自然に含める

バズりやすい要素：具体的数字・意外性・あるある共感・個人の体験談・リスト形式
"""


def generate_ideas(
    client: anthropic.Anthropic,
    account: dict,
    trend_data: dict,
    past_posts: str,
) -> str:
    hour = datetime.now(JST).hour
    closest = min(_TIME_CONTEXT, key=lambda h: abs(h - hour))

    prompt = _PROMPT.format(
        persona=account["persona"],
        pillars="\n".join(f"- {p}" for p in account["pillars"]),
        buzz_posts=trend_data.get("buzz_posts") or "（取得できませんでした）",
        industry_news=trend_data.get("industry_news") or "（取得できませんでした）",
        past_posts=past_posts or "（データなし）",
        algorithm_tips=trend_data.get("algorithm_tips") or "（取得できませんでした）",
        x_trends=trend_data.get("x_trends") or "（取得できませんでした）",
        google_trends=trend_data.get("google_trends") or "（取得できませんでした）",
        time_context=_TIME_CONTEXT[closest],
    )

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text
