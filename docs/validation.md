# 受入検証記録

実施日: 2026-11-14。以下の前半は初期MVP（NOAH公式2025年、当時private）の検証。現在の公開版は末尾の拡張記録を参照:
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
3. NOAH2016〜2018年の別公式資料、新日本の2016〜2024年と全日本の2024年の取得を検証する。
4. STARDOM等を追加する前に、各取得条件と一覧構造を調査する。

## 公開ダッシュボード・3団体への拡張（2026-11-14）

利用者が公開リポジトリへ変更し、GitHub Pagesでの公開を明示的に指定。記事全文・画像・カードを含めず、既存JSONL正本と抽出した事実値・集計を公開する。

|情報源|収集済み期間|大会数（海外・国不明を含む）|観衆数値あり|
|---|---|---:|---:|
|NOAH|2019-01-06〜2025-12-23|629|487|
|新日本|2025-01-04〜2025-12-22|157|153|
|全日本|2025-01-02〜2025-12-31|80|68|

- 合計866大会。NOAHの初期3件のparser更新等は別観測として保持し、分析IDで重複排除する。履歴行数と大会数は異なる。
- NOAH2019〜2024年は533リンク全件をHTTP取得。初回は会場空欄の6件が失敗。元HTMLで大会名・日程・出典IDが確認できたため、venue_raw=nullとvenue_unknown警告を許容する修正後、6件だけ再取得し保存した。架空の会場・国・観衆は補わない。初回診断は `data/coverage/noah/backfill_2019_2024_initial.json` に保持。
- NOAH2016〜2018年の年選択肢なしを再確認し、unsupported coverageを保存。2019〜2025年のサイト一覧の巡回は確認済みだが、掲載されていない現実の大会を含む網羅性は保証しない。
- 新日本2025年は11一覧ページ・157大会、全日本2025年は5年別一覧ページ・80大会、各失敗0。少数3件→全体の再取得で既存3件を増殖させず、不変3と新規154/77を確認。
- 基本国内集計の2025年: NOAH 96大会・判明88（91.67%）、新日本153大会・判明149（97.39%）、全日本80大会・判明68（85%）。海外4大会と国不明の大会は基本国内集計から除外する。
- NOAHの古い配信会場・特設会場など国不明の記録を保持し、国内へ推測分類しない。NOAH the HOME等の「日程」と実収録日が一致するかは未確認。日時は公式項目の原値を基準とする。
- ブラウザー検証: Chromiumで1440pxのPCと390pxのモバイルを確認。団体フィルター、合計/平均切替、タブ、検索、CSVリンクが動作し、JavaScript例外0、モバイル横はみ出しなし。スクリーンショットはローカル `var/browser/`（Git対象外）。
- 最終ローカル検証: pytest 25件成功、JavaScript集計テスト成功、ruff成功。3団体と全期間の実データでdbtの20モデル/11品質テストを実行。未登録会場で情報源ごとの国判定根拠が異なる場合もdimの会場IDが重複しないことを回帰テストした。
- ダッシュボードの前年比較は、前年に未収集の団体がある場合や対象月のcoverageが不足する場合に抑止。異なる団体集合を比較して架空の増減率を表示しない。
- 静的配布物は `site/`＋最新exportsだけ。公開URL: https://yutarowada0402.github.io/prowrestling-attendance/ 。リポジトリ公開・Pages公開は利用者の明示依頼による。
- 公開URLをHTTP 200で確認し、Chromiumで公開ページの団体フィルター・タブ・検索・CSV・モバイル表示を検証。JavaScript例外0、横はみ出しなし。
- [最終CI](https://github.com/yutarowada0402/prowrestling-attendance/actions/runs/43587809419) と [Pages初回公開](https://github.com/yutarowada0402/prowrestling-attendance/actions/runs/43587809520) はsuccess。HTML追跡漏れを修正したcommitで公開された。
- [3団体手動収集](https://github.com/yutarowada0402/prowrestling-attendance/actions/runs/43587823343): 2025年の一覧333件を発見（NOAH96、新日本157、全日本80）、各団体のlimit=1で詳細を取得。1 changed / 2 unchanged / 0 failed、収集statusはlimit適用を反映したpartial。dbt build/export/品質ゲート成功し、診断Artifactも保存された。再実行で重複を増やさないことを確認。
- 収集データcommit [73e68e8](https://github.com/yutarowada0402/prowrestling-attendance/commit/73e68e891b7d5fe22122275bb4d8ca749a42bb80) がmainへpushされ、[その後のPages公開](https://github.com/yutarowada0402/prowrestling-attendance/actions/runs/43587963147) もsuccess。収集→正本commit→静的サイト再公開を実動確認した。
