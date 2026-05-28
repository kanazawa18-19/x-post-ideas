import json
import re
import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def _parse_int(s: str) -> int:
    try:
        return int(str(s).replace(",", "").strip())
    except (ValueError, AttributeError):
        return 0


def _load_creds(credentials_path: str) -> Credentials:
    """credentials.jsonを読み込む。private_keyの改行・PEMヘッダー崩れを自動修正する。"""
    text = open(credentials_path).read()
    try:
        info = json.loads(text)
    except json.JSONDecodeError:
        def fix_pk(m: re.Match) -> str:
            return m.group(1) + m.group(2).replace("\r\n", "\\n").replace("\r", "\\n").replace("\n", "\\n") + '"'
        fixed = re.sub(r'("private_key"\s*:\s*")(.*?)(?<!\\)"', fix_pk, text, flags=re.DOTALL)
        info = json.loads(fixed)

    # PEMヘッダー・フッターに混入した空白・改行を修正
    # 例: "-----BEGIN PRIVATE\n  KEY-----" → "-----BEGIN PRIVATE KEY-----"
    if "private_key" in info:
        pk = info["private_key"]
        pk = re.sub(r"-----BEGIN\s+PRIVATE\s+KEY-----", "-----BEGIN PRIVATE KEY-----", pk)
        pk = re.sub(r"-----END\s+PRIVATE\s+KEY-----", "-----END PRIVATE KEY-----", pk)
        info["private_key"] = pk

    return Credentials.from_service_account_info(info, scopes=SCOPES)


def get_top_posts(spreadsheet_id: str, sheet_name: str, credentials_path: str, top_n: int = 8) -> str:
    creds = _load_creds(credentials_path)
    gc = gspread.authorize(creds)
    sheet = gc.open_by_key(spreadsheet_id).worksheet(sheet_name)

    rows = sheet.get_all_values()
    if len(rows) < 2:
        return ""

    header = rows[0]
    try:
        text_idx = header.index("ポスト本文")
        imp_idx = header.index("インプレッション数")
        like_idx = header.index("いいね")
    except ValueError:
        return ""

    data_rows = [r for r in rows[1:] if len(r) > imp_idx and r[text_idx].strip()]
    data_rows.sort(key=lambda r: _parse_int(r[imp_idx]), reverse=True)

    lines = ["【過去の高パフォーマンス投稿（参考にすべきスタイル・内容）】"]
    count = 0
    for row in data_rows:
        if count >= top_n:
            break
        imp = _parse_int(row[imp_idx])
        likes = _parse_int(row[like_idx]) if len(row) > like_idx else 0
        if imp == 0:
            continue
        text = row[text_idx].strip().replace("\n", " ")[:120]
        lines.append(f"・{imp:,}imp／{likes}いいね：{text}")
        count += 1

    return "\n".join(lines) if count > 0 else ""
