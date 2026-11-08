# X投稿ネタ自動生成ツール｜セットアップマニュアル（パターン1：フル機能版）

> **このパターンはエンジニア向けです。**
> Pythonの操作やターミナル（黒い画面）の操作に慣れている方向けの手順です。
> 慣れていない方はパターン2（GAS版）またはパターン3（Colab版）をご利用ください。

---

## このツールでできること

- Xのリアルタイムトレンドを自動収集
- Googleトレンド（日本）を自動収集
- 同ジャンルのバズ投稿を自動参照
- 業界ニュース・ノウハウをWeb検索で取得
- 自分の過去投稿の中から高パフォーマンス投稿を参照
- 上記をもとにXの投稿案を10個生成
- Slackの指定チャンネルに自動投稿

---

## 必要なもの（事前に用意してください）

| 必要なもの | 説明 | 費用 |
|---|---|---|
| Anthropic APIキー | AIの利用に必要 | 従量課金（月数百円〜） |
| Slack Botトークン | Slackへの自動投稿に必要 | 無料 |
| Googleサービスアカウント | スプレッドシートの読み取りに必要 | 無料 |
| Xアカウント（ログイン済み） | トレンド収集に必要 | 無料 |
| Python 3.10以上 | ツール本体の実行環境 | 無料 |

---

## STEP 1｜Pythonのインストール確認

ターミナル（Macは「ターミナル」アプリ、Windowsは「コマンドプロンプト」）を開き、以下を入力してEnterを押してください。

```
python --version
```

`Python 3.10.x` のように表示されればOKです。
表示されない場合は https://www.python.org からPythonをインストールしてください。

---

## STEP 2｜ツールのダウンロード

ターミナルで以下を実行してください。

```
git clone https://github.com/kanazawa18-19/x-post-ideas.git
cd x-post-ideas
```

---

## STEP 3｜必要なライブラリのインストール

```
pip install -r requirements.txt
playwright install chromium
```

---

## STEP 4｜Anthropic APIキーの取得

1. https://console.anthropic.com にアクセスしてアカウントを作成
2. 左メニューの「API Keys」をクリック
3. 「Create Key」ボタンをクリック
4. 表示されたキー（`sk-ant-...` で始まる文字列）をコピーして安全な場所に保存

---

## STEP 5｜Slack Botの作成とトークン取得

1. https://api.slack.com/apps にアクセス
2. 「Create New App」→「From scratch」をクリック
3. App名（例：`投稿ネタBot`）とワークスペースを選んで「Create App」
4. 左メニュー「OAuth & Permissions」をクリック
5. 「Bot Token Scopes」の「Add an OAuth Scope」から以下を追加：
   - `chat:write`
6. ページ上部の「Install to Workspace」をクリックして許可
7. 表示された「Bot User OAuth Token」（`xoxb-...` で始まる文字列）をコピー

**投稿先チャンネルにBotを招待する**
Slackで投稿先のチャンネルを開き、メッセージ欄に `/invite @投稿ネタBot` と入力してEnter

---

## STEP 6｜Googleサービスアカウントの作成

> アナリティクス（過去の高パフォーマンス投稿の参照）を使う場合のみ必要です。
> 使わない場合はこのSTEPをスキップしてください。

1. https://console.cloud.google.com にアクセス
2. 上部の「プロジェクトを選択」→「新しいプロジェクト」で適当な名前（例：`x-post-ideas`）でプロジェクト作成
3. 左メニュー「APIとサービス」→「ライブラリ」→「Google Sheets API」を検索して「有効にする」
4. 左メニュー「APIとサービス」→「認証情報」→「認証情報を作成」→「サービスアカウント」
5. 名前を入力して「作成して続行」→「完了」
6. 作成したサービスアカウントのメールアドレス（例：`xxx@xxx.iam.gserviceaccount.com`）をコピー
7. サービスアカウントをクリック→「キー」タブ→「鍵を追加」→「JSON」→ダウンロード
8. ダウンロードしたJSONファイルを `credentials.json` という名前でツールのフォルダに保存
9. アナリティクスデータが入っているGoogleスプレッドシートを開き、「共有」ボタンから手順6のメールアドレスを「閲覧者」として追加

---

## STEP 7｜X（Twitter）のCookieをエクスポート

> Xのトレンドをリアルタイムで収集するために必要です。

1. Google ChromeにCookie Export拡張機能をインストール
   - 拡張機能名：「EditThisCookie」または「Cookie-Editor」
2. Chromeで https://x.com にログイン
3. 拡張機能のアイコンをクリック→「Export」（JSON形式）
4. コピーした内容を以下の形式で `cookies.json` として保存：

```json
{
  "cookies": [ ここにコピーした内容を貼り付け ]
}
```

---

## STEP 8｜設定ファイルの編集

`config.py` をテキストエディタで開き、以下を自分の情報に書き換えてください。

```python
CHANNEL_ID = "Slack投稿先チャンネルのID"
SPREADSHEET_ID = "スプレッドシートのID（URLのd/〜/editの間の文字列）"
```

各アカウントの情報も編集してください：

```python
{
    "name": "あなたの名前",
    "thread_ts": "SlackスレッドのタイムスタンプID（省略可）",
    "sheet_tweet": "スプレッドシートのシート名",
    "persona": "あなたのXアカウントのキャラクター・専門領域の説明",
    "pillars": [
        "発信テーマ1",
        "発信テーマ2",
    ],
    "keywords": [
        "キーワード1",
        "キーワード2",
    ],
}
```

---

## STEP 9｜環境変数の設定

ツールのフォルダに `.env` というファイルを作成し、以下を記入してください。

```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxx
```

---

## STEP 10｜動作確認

ターミナルで以下を実行してください。

```
python main.py
```

Slackに投稿ネタが届けば成功です。

---

## 定期実行の設定（自動化）

### Macの場合（cron）

ターミナルで `crontab -e` を入力して以下を追加（毎日7時・12時・19時・22時に実行する例）：

```
0 7,12,19,22 * * * cd /path/to/x-post-ideas && python main.py
```

### GitHub Actionsの場合（クラウドで自動実行）

リポジトリを自分のGitHubにforkし、Settings→Secretsに以下を追加：
- `ANTHROPIC_API_KEY`
- `SLACK_BOT_TOKEN`

`.github/workflows/` 内のYMLファイルでスケジュールを設定できます。

---

## よくある問題と解決策

| 症状 | 原因 | 解決策 |
|---|---|---|
| `ModuleNotFoundError` | ライブラリが入っていない | `pip install -r requirements.txt` を再実行 |
| Xトレンドが取れない | Cookieが古い・ログアウトしている | Xに再ログインしてCookieを再エクスポート |
| Slackに届かない | BotがチャンネルにいないかTokenが違う | `/invite @Bot名` を再実行、Tokenを確認 |
| スプレッドシートが読めない | 共有設定が漏れている | サービスアカウントのメールアドレスを共有に追加 |
| `RateLimitError` | APIの呼び出し回数が多すぎる | しばらく時間を置いて再実行 |
