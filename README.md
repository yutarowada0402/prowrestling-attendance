# prowrestling-attendance

公式発表のプロレス興行・公表観衆を、出典と訂正履歴を残して蓄積するデータプロジェクト。**NOAH・新日本・全日本の公式情報源**に対応し、JSONLをこの公開リポジトリへ蓄積します。NOAHは2019〜2025年、新日本・全日本は2025年を取得済み。記事全文・画像・試合カードは公開しません。

公開ダッシュボード: **https://yutarowada0402.github.io/prowrestling-attendance/**

年・主集計団体・国内/全開催地を選び、開催数、公表観衆合計、平均・中央値、判明率、月別推移、会場別順位、興行検索と出典、月別収集状況を確認できます。団体比較タブでは、年ごとに総動員・興行数・平均・中央値・判明率・最大興行・動員シェアと月別推移を団体別に並べて確認できます（比較は同一条件で揃えた年単位のみ）。前年比較は同一団体と対象月の巡回記録が揃った場合だけ表示し、欠損期間を0人として比較しません。

## セットアップと実行

Python 3.11以降（検証は3.11）、[uv](https://docs.astral.sh/uv/getting-started/installation/) が必要です。依存バージョンは `uv.lock` に固定。

```bash
git clone https://github.com/yutarowada0402/prowrestling-attendance.git
cd prowrestling-attendance
uv sync --frozen
uv run pytest -q
uv run wrestling build
uv run wrestling export
```

初回の依存インストール以降、テスト・build・exportに外部サイトとの通信は不要です。pytestの大会はすべて明示的な合成fixtureで、一時ディレクトリだけに出力します。実データのexportsに混ぜません。dbtはbuildコマンド内で `dbt build --project-dir dbt --profiles-dir dbt` を実行し、モデルと品質テストを作成します。

```bash
# 公式一覧から発見し、URL/stateと巡回状況を保存（詳細は取得しない）
uv run wrestling discover --source noah --from 2025-01-01 --to 2025-12-31
# dry-runはrobotsと一覧の通信あり、詳細通信・ファイル保存なし
uv run wrestling collect --source noah --from 2025-01-01 --to 2025-12-31 --limit 20 --dry-run
# 最初は小さく検証し、上限を外して全一覧へ
uv run wrestling collect --source noah --from 2025-01-01 --to 2025-12-31 --limit 20
uv run wrestling collect --source noah --from 2025-01-01 --to 2025-12-31
# 今日を含む過去30日。過去分は上の日付指定でbackfill
uv run wrestling update --source noah --lookback-days 30
# 新日本・全日本（最初は小さな上限で確認）
uv run wrestling collect --source njpw --from 2025-01-01 --to 2025-12-31 --limit 20
uv run wrestling collect --source ajpw --from 2025-01-01 --to 2025-12-31 --limit 20
# 一覧を再確認し、保存済みの失敗URLだけを再試行
uv run wrestling collect --source noah --from 2019-01-01 --to 2024-12-31 --retry-failed
uv run wrestling build
uv run wrestling export
uv run wrestling validate
```

`--from/--to` は両端含む開催日です。`--limit` は詳細取得件数だけを制限し、一覧巡回は制限しません。0なら詳細0件。NOAHのupdateは結果一覧と予定一覧、新日本・全日本は結果一覧を確認します。過去の予定に観衆欄がないだけで開催済みとしません。未来ページはscheduledとして区別し、通常updateの抽出範囲は今日までです。別rootを使う場合 `wrestling --root /path ...`。先にそのrootへ config、dbt、seeds/overrides を配置してください。

収集が一部失敗した場合、既存観測を保持して失敗URLをstateへ記録し終了コード2。次の同範囲collectで再試行します。事前のrobots取得失敗等は終了1。403・CAPTCHA・robots禁止を回避しません。リダイレクトは要確認として停止。未知のHTMLは欠損を推測で埋めず失敗させます。各工程は別モジュールです（CLI / HTTP / 一覧発見 / 詳細parser / 保存 / DuckDB loader / dbt変換 / export）。

## 保存と出力

|場所|用途|
|---|---|
|`data/observations/noah/2025.jsonl`|Git管理する抽出履歴。同じ内容で増殖しない|
|`data/state/noah.json`|発見済みURL、採用観測pointer、確認時刻、失敗、ETag|
|`data/overrides/events.csv`|理由つき手動統合・分割・修正|
|`data/seeds/`|団体・会場・別名の手動マスター|
|`data/coverage/noah/`|月別巡回状態と直近実行レポート|
|`var/raw/`|圧縮HTML。ローカルのみ、Git除外|
|`var/attendance.duckdb`|再生成できる派生DB。Git除外|
|`exports/`|CSV/JSONと品質サマリー。Git管理|

必須出力は events、attendance_monthly、attendance_yearly、attendance_by_venue のCSV/JSONとquality_summary.json。曜日・地域・YTD・共催参考・coverage・統合候補も出力します。JSONは日付ISO形式とnull、CSVのnullは空セルです。データを変更したらbuild→exportで再生成してください。

基本比較は国内・開催済み・主集計団体の大会。観衆不明でも開催数へ入り、数値を0へ補完しません。0は明示的無観客のみ。判明値だけで合計・平均・中央値を作り、判明率を併記します。公表観衆はユニーク観戦者数・有料入場者数・売上ではありません。詳しい採用・増減分解・前年比・合同興行のルールは [methodology](docs/methodology.md)、項目定義は [data_dictionary](docs/data_dictionary.md)。

`listing_complete` は指定期間の当該サイト一覧を確認できた意味に限定し、現実の全興行の網羅性ではありません。観衆判明率と収集網羅性は別です。年途中の比較はYTD表を使い、前年通年と直接比較しないでください。会場マスター未登録は未分類のまま出力します。

## GitHub Actions

`pages.yml` は `site/` のHTML/CSS/JavaScriptと最新exportsを `dist/` へまとめ、GitHub Pagesへ公開します。データ更新pushと収集workflowの成功後に再公開するため、GITHUB_TOKENのcommitが通常のpush workflowを起動しない場合も更新できます。Pages権限はdeployジョブだけpages:write/id-token:write。raw HTML/JSON、ログ、DBは公開Artifactへ入れません。

ローカル表示と検証:

```bash
uv run python scripts/build_site.py
uv run python -m http.server 8877 --bind 127.0.0.1 --directory dist
# 別ターミナル。Node.js で集計のnull/0/重複排除/同一YTDを検証
node tests/test_site.mjs
# 任意のブラウザー検証（Playwright/Chromiumの準備が必要）
uv run --with playwright python scripts/browser_smoke.py http://127.0.0.1:8877/
```

この検証環境では同梱Nodeのlibatomic不足のため、Playwright実行時に `PLAYWRIGHT_NODEJS_PATH=/usr/bin/node` を指定しました。画面は静的HTMLで、データ閲覧にPythonサーバーやDB接続は不要です。

- `ci.yml`: push/PRでオフラインparser・保存・集計テスト、合成fixtureのdbt build、追跡データのdbt buildと品質テスト。外部サイトを巡回しません。
- `collect.yml`: workflow_dispatchと日次cron（手動実行成功後に有効化）。mainの前回データをcheckout→収集→dbt build→export→品質検証→変更があるdata/exportsだけcommit/push。GITHUB_TOKENで永続化します。Artifact/キャッシュは正本ではありません。
- 手動backfillは source（noah/njpw/ajpw/all）、mode=collect、date_from/to、limit（各団体0〜500、最大367日）を指定。日次はsource=allで3団体を順に直近30日更新。入力は環境変数からPythonで検証し、シェルへ直接展開しません。
- concurrencyで同時更新防止。品質失敗ならcommitしません。収集だけ部分失敗した場合は正常データと失敗stateを検証後commitし、ジョブは最後に失敗表示します。summaryに取得・変更・不変・失敗・未公表・競合・期間を出します。
- 書込権限はcollectジョブだけcontents:write、他はread。push競合は通常pushの拒否で明示失敗し、force push/rebaseで上書きしません。GITHUB_TOKENによるデータcommitから収集は再帰起動しません（収集トリガーは手動/将来cronのみ）。
- ブランチ保護でbotのpushが拒否される場合は、管理者が当該データ更新を許すルールを設定するか、収集を専用ブランチへpushしPRを作る方式へ変更してください。MVPはmain直接保存です。
- 診断ログとdbt結果を7日Artifactへ。save_html=trueのとき、当該Actions実行で取得したHTMLも7日保存。期限切れ後は元HTMLを復元できません。長期監査が必要なら別ストレージに拡張してください。
- 日次cronは手動実行と保存commitの成功を確認して有効化済みです。設定値は `17 21 * * *` UTC = 翌日06:17 JST。GitHubの定期実行は遅延し得ます。10年分のbackfillを日次へ混ぜません。初回の時刻指定起動は次の定期実行で確認します。

```bash
gh workflow run collect.yml --ref main -f mode=collect \
  -f source=all -f date_from=2025-01-01 -f date_to=2025-12-31 -f limit=3
gh run list --workflow collect.yml
gh run view <run-id> --log-failed
```

## 調査・検証・制約

利用条件・robots・取得構造・掲載範囲は [sources](docs/sources.md)。自動取得・事実データ再配布の明示的許諾は未確認です。robotsのAllow/404を再配布許諾とは扱いません。利用者の指示で公開リポジトリとGitHub Pagesに事実項目・出典URL・集計だけを公開しています。元記事・画像等の権利を本コードが許諾するものではありません。利用条件が明示的に禁止へ変わる場合、その情報源を停止して公開範囲も見直します。

2025年一覧は96大会を発見。実取得と受入確認の最終結果は [validation](docs/validation.md)、機械的な最新件数・期間・観衆判明率・失敗は `exports/quality_summary.json` と `data/coverage/noah/latest_run.json` が正本です。10件の出典照合記録は [manual_checks](docs/manual_checks.csv) を参照。照合者がCodexの場合、人間による独立レビュー済みとは説明しません。

検証対象は25件のpytest、20モデル/11品質テストのdbt build、JavaScript集計テスト、PC/モバイルのChromium操作テスト。採用観測の復帰を正確に再現するためstateも正本として保持します。3情報源はいずれも公式で同一優先度です。非公式ソースを追加する前に優先順位を一般化します。主催/共催roleと会場マスターは継続整備。STARDOMと二次サイトは未実装。NOAHの2016〜2018年は現行一覧に年選択肢がなく未対応、新日本の過去年と全日本の2024年以前は収集未実行です（掲載範囲の調査結果はsources参照）。

GitHub作成・push権限が使えない環境で再構築する場合:

```bash
git init -b main
git add .
git commit -m 'Implement NOAH attendance MVP'
gh repo create prowrestling-attendance --private --source=. --remote=origin --push
```
