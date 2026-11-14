# 受入検証記録

実施日: 2026-11-14、対象: NOAH公式2025年、private repository:
https://github.com/yutarowada0402/prowrestling-attendance

## 実データ

最初に3大会を取得し、日程・開始・会場・観衆原文を確認した後、2025年の結果一覧を全巡回した。

- 指定範囲: 2025-01-01〜2025-12-31（実際に発見した開催日: 01-01〜12-23）。
- 一覧: `/result/` と `/result/?y=2025`、発見96大会、詳細96大会取得、失敗0。
- 履歴96行、分析96大会。初期3件を全件実行で再取得した際は変更0・不変3、残り新規93。重複なし。
- 国内開催済み96大会。観衆判明88、未公表/空欄8、判明率91.6667%。競合0。
- 公表観衆合計70,154人、判明興行平均797.2045人、中央値443.5人。不明を0扱いしていない。
- 全12か月の一覧巡回状況 listing_complete。現実の全興行の網羅性を保証しない。
- 10大会の日付・観衆について、parserとは別に保存済みHTMLのdt/dd欄を抽出しCodexが値を照合した記録を `docs/manual_checks.csv` に保存。**人間による独立レビューは未実施**（human_reviewed=false）。仕様の「人手確認」を人間が確認する意味に厳密に取る場合、この条件は未達。
- 未公表ID: 683、684、685、686、687、740、741、742。未公表・空欄を架空の値で補完していない。
- 国不明だった2会場は自治体・施設の所在地資料で手動seed補完（sources.md参照）。元観測は保持。
- `update --lookback-days 30 --dry-run` で2026年の結果一覧・予定一覧の構造と7URL発見を検証。詳細取得・保存はしていない。

## オフライン

- pytest: 観衆表記9例、日付と時刻、予定/結果区別、URL発見と正規化、403停止、429と共通レート制限、再試行上限、履歴/訂正/再構築/共催、部分失敗/dry-run/403保全、0人/全件不明/ID安定/過去内容への復帰。
- dbt build: staging→intermediate→marts、20モデルと11品質テスト。全成功を確認。
- 同一履歴からbuild/exportを繰り返し、events.jsonがバイト単位で一致するテストあり。
- ruff check、git diff --checkを実施。
- 合成fixtureは `tests/fixtures/synthetic_*.html`、テスト出力は一時rootだけ。実データに合成値を混ぜていない。
- 検証環境: Python3.11.14 / httpx0.28.1 / beautifulsoup4 4.15.0 / DuckDB1.5.6 / dbt-core1.12.7 / dbt-duckdb1.11.1 / pytest9.2.0。uv.lockに依存解決結果を固定。

## GitHub Actions

- クリーンcheckoutからの[CI実行](https://github.com/yutarowada0402/prowrestling-attendance/actions/runs/43583186658): success。uv sync --frozen、ruff、19 pytest（fixture内のdbt build含む）、追跡96件のdbt build/exportが完走。
- [手動収集実行](https://github.com/yutarowada0402/prowrestling-attendance/actions/runs/43583200939): success。2025年全一覧を発見し、limit=3で詳細再取得3、変更0、不変3、失敗0。JSONLは96行のまま。件数制限実行なのでrun statusはpartialと正確に表示。
- GITHUB_TOKENでstate/coverageの変更がmainへ保存されたcommit: [e5f2210](https://github.com/yutarowada0402/prowrestling-attendance/commit/e5f2210)。force pushなし。ローカルへfast-forwardで取得して観測数96を確認。
- 診断Artifactの `var/run-summary.json` をダウンロードして上の件数を確認。本文HTMLのArtifact保存は任意フラグで、初回は無効。
- 手動実行・保存commit成功後に日次cron `17 21 * * *` を有効化。06:17 JST相当、直近30日を更新。初回の時刻指定による自動起動は未検証（次の実行で確認）。

## 次に必要な作業

1. 人間による10件の独立レビューと情報源の継続利用条件の確認。
2. 会場マスター（所在地・名称変更）と合同興行の主催/共催roleの資料整備。
3. NOAH2019〜2024年を小さい年範囲で検証し、2016〜2018年の別公式資料の有無を調査。
4. 新日本・全日本の取得条件と一覧構造を調査し、公式優先順位を一般化してからadapter追加。
