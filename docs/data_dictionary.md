# データ辞書

## 観測 JSONL

UTF-8、1行1JSON object、キーは辞書順、行は source_event_id/fetched_at/observation_id 順。改行LF、JSON欠損はnull。既存履歴を読んで追記相当の内容を一時ファイルへ出力し fsync と os.replace で原子的に置換する。年は当該観測の開催年で、年訂正で両年に分かれても全履歴から統合する。

|項目|意味|
|---|---|
|observation_id|分析項目＋parser_versionのSHA-256|
|source / source_event_id / source_url|情報源、元大会ID、正規化出典URL|
|first_observed_at|source大会を最初に観測したUTC時刻|
|fetched_at|この内容を初めて抽出した取得時刻（UTC、Z）|
|parser_version / response_hash|抽出ロジック版 / 元HTML SHA-256|
|event_date / start_time|開催地の日付YYYY-MM-DD / HH:MM、不明はnull|
|timezone / country_code|根拠がある国内はAsia/Tokyo / JP、それ以外はnull|
|prefecture_raw|公式の会場地域・一覧見出しから明示的に確認できた都道府県。古い観測または不明はnull|
|promotion_raw / event_name_raw / venue_raw|元の表記|
|attendance_raw / attendance_reported|観衆原文 / 非負整数またはnull|
|attendance_status|reported / unknown / explicitly_zero|
|attendance_note|札止め・満員などの補足、数字がない場合は原文|
|event_status|held / scheduled / cancelled / postponed / unknown|
|extraction_warnings|構造化警告コードの配列|

## 正本と派生物

- `data/state/noah.json`: 正規化URL、一覧由来区分、開催日、last_checked_at、last_observation_id、error、ETag/Last-Modified。エラーでも過去の成功pointerを維持。ETagは記録のみで毎回全文再確認する。
- `data/overrides/events.csv`: 手動ID対応・分割・補正とreason。列の使い方はmethodology参照。
- `data/mappings/event_ids.csv`: 情報源大会IDから日付に依存しない初期event_idへの永続対応表。build時に未登録IDだけ追加し、既存対応は保持。統合・分割はoverrideで重ねる。
- `data/seeds/*.csv`: 団体/会場/別名マスター。
- `data/coverage/noah/YYYY-MM.json`: 当該範囲の巡回状況。latest_run.jsonは直近実行件数と失敗URL。
- `var/raw/noah/<hash>.html.gz`: 非公開ローカルHTMLキャッシュ（Git除外）。
- `var/attendance.duckdb`: JSONLとstate、seeds、override、coverageから再生成する派生DB。
- `fct_events`: 安定event_id、開催日・開始・国内外・状態、主団体、会場、採用数値と出典/原文/採用観測ID、競合・消失フラグ、手動理由、ISO曜日。
- `event_source_links`: event_id と情報源IDの対応、`bridge_event_promotions`: 主集計団体と共催団体の関係。
- `exports/*.csv` と `*.json`: 安定列順/行順、CSVの欠損は空セル、JSON欠損はnull。日付はYYYY-MM-DD。quality_summaryの率も数値、0件の率はnull。

HTMLは本文を含むためGitへ追加しない。再配布可能な最小合成fixture以外はtestsへ転載しない。

新日本の元レスポンスはJSONだが、ローカルrawキャッシュの互換上 `.html.gz` の拡張子で保存する。中身を自動的にHTMLとみなさず、source adapterが形式を決める。Git/Pagesへ元レスポンスを公開しない。会場欄が空でもsource ID・開催日・大会名が確認できる場合は venue_raw=null と venue_unknown 警告を保存する。
