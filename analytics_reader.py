import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def _parse_int(s: str) -> int:
    try:
        return int(str(s).replace(",", "").strip())
    except (ValueError, AttributeError):
        return 0


def get_top_posts(spreadsheet_id: str, sheet_name: str, credentials_path: str, top_n: int = 8) -> str:
    creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
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
