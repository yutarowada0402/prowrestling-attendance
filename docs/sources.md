# 情報源の調査記録

調査日: 2026-11-14（JST）。MVP adapter は NOAH のみ。

## NOAH 公式

- 起点: https://www.noah.co.jp/
- 一覧: https://www.noah.co.jp/result/ 、2025年 https://www.noah.co.jp/result/?y=2025
- HTML の `select.yearselect` と change handler `./?y=` を実取得して確認。2019〜2026年の選択肢。2016〜2018年は未対応。2019〜2024年は選択肢の存在だけを確認し、全大会の詳細掲載は未検証。
- 2025年一覧は96件の `article.c-schedule-item`。日程の dt/dd から日付、実在する `/schedule/<ID>/` のリンクを抽出する。ページID総当たりなし。ページ送りは next/pager/pagination の実リンクだけ巡回し、既訪問検出と100ページ上限を設定。
- 詳細: https://www.noah.co.jp/schedule/628/ 、https://www.noah.co.jp/schedule/733/ を確認。`dl.desc-list` の `日程/開始/会場/観衆`、親 `dl.list > dt.term` の大会名を抽出。記事投稿日、レポート、カードは取得項目に使わない。
- robots: https://www.noah.co.jp/robots.txt は直接HTTP取得で404（2026-11-14）。指令がないことは自動取得・再配布の許可を意味しない。各実行で再確認し、指令・crawl-delay・request-rate があれば適用。
- 主サイトのフッターでサイト全体の利用規約へのリンクは確認できず。自動取得・事実データ再配布の明示的許諾は未確認。
- プライバシーリンク: https://cyber-fight.co.jp/privacy-policy/ 。再利用規約とは扱わない。
- 通販規約 https://shop.noah.co.jp/policies/terms-of-service は別サービス。主サイトの収集許諾へ流用しない。
- 公開された正式APIは確認できず。通常HTTP＋BeautifulSoupで取得可能。Playwright不要。
- 通信条件: 独自User-Agent、ドメイン単位直列、開始間隔3秒以上、30秒timeout、最大3再試行、指数バックオフと429 Retry-After。403/CAPTCHA/robots禁止で停止。リダイレクトは自動追従せず要確認エラーとする。
- 一覧・詳細の構造が変わった場合は警告/失敗にして既存履歴を保持。全文・画像はGitへ格納しない。
- 一覧が掲載する大会だけが母集団。掲載前に削除された大会、一覧外の特別興行、過去の中止情報、海外判定ができない会場等に不足の可能性がある。
- 実行結果・失敗URL: `data/coverage/noah/latest_run.json`、月別巡回状況は同ディレクトリ。データが増えても現実の全興行の網羅性を主張しない。

## 未実装

会場マスターの補足（同日調査）: 地域接頭辞のなかった2会場は、[島田市公式](https://www.city.shimada.shizuoka.jp/kanko-docs/1985.html) と [スポーツ庁施設情報](https://cocospo.go.jp/facility/30716) で静岡県島田市、[Gメッセ公式](https://www.g-messe-gunma.jp/) で群馬県高崎市を確認し、国内会場seedへ登録した。原観測は修正せず、分析モデルの国・時区はseedで補完。

新日本 https://www.njpw.co.jp/ 、全日本 https://www.all-japan.co.jp/ 、STARDOM https://wwr-stardom.com/ は次段階。各利用条件・robots・対象期間・一覧構造は未調査。CAGEMATCH、prowrestlingdata、yurutameeeee はMVPの取得対象外。

## 実装時のライブラリ資料

- HTTPX: https://www.python-httpx.org/advanced/transports/ （transport retry だけでは429処理が不足するため自前の明示的制御）
- BeautifulSoup: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
- uv: https://docs.astral.sh/uv/guides/projects/
- dbt DuckDB adapter: https://github.com/duckdb/dbt-duckdb
- Actions: https://github.com/actions/checkout 、https://github.com/astral-sh/setup-uv 、https://github.com/actions/upload-artifact 。安定した既存majorを利用し、実行で互換性を検証する。
