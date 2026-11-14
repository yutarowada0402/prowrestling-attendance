# 情報源の調査記録

調査日: 2026-11-14（JST）。実装済み adapter は NOAH、新日本、全日本。

## NOAH 公式

- 起点: https://www.noah.co.jp/
- 一覧: https://www.noah.co.jp/result/ 、2025年 https://www.noah.co.jp/result/?y=2025
- HTML の `select.yearselect` と change handler `./?y=` を実取得して確認。2019〜2026年の選択肢。2016〜2018年は未対応。2019〜2024年の一覧533大会を巡回した。
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

## 会場マスター

会場マスターの補足（同日調査）: 地域接頭辞のなかった2会場は、[島田市公式](https://www.city.shimada.shizuoka.jp/kanko-docs/1985.html) と [スポーツ庁施設情報](https://cocospo.go.jp/facility/30716) で静岡県島田市、[Gメッセ公式](https://www.g-messe-gunma.jp/) で群馬県高崎市を確認し、国内会場seedへ登録した。原観測は修正せず、分析モデルの国・時区はseedで補完。

追加会場は [新木場1stRING公式](https://www.1st-ring.com/access.html)、[大阪府公式](https://www.pref.osaka.lg.jp/shisetsu/o180070/shisetsu_000005.html)、[カルッツ公式](https://culttz.city.kawasaki.jp/access/) の所在地で確認。海外4会場の国は新日本の元会場表記「アメリカ・」「イギリス・」を根拠とする。根拠のない特設会場・配信会場の国は不明のまま。

## 新日本公式

- 起点: https://www.njpw.co.jp/ 。HTMLはVue SPAで、大会の静的HTML抽出は不可。
- 公式JSの実参照から確認した無認証JSONをHTTP取得する。正式な公開API仕様書を確認したものではない。
- 年一覧: https://app.njpw.co.jp/series/tournaments/results/search-year.json （200、2007〜2026年）。取得済みは2025年のみ。
- 年別一覧: https://app.njpw.co.jp/series/tournaments/results/year/2025/1.json 。`all_count=11` を公式UIのページ数として使用し、`Series[].tournaments[]` の実在post_id/event_start_dateを発見。2025年は157大会。
- 詳細取得の実参照: `https://app.njpw.co.jp/tournament/posts/{post_id}.json`。出典ページ例 https://www.njpw.co.jp/tournament/result/600329 。`schedule_title/event_start_date/start_time/venue.stadium_name/venue.prefecture/spectators` の事実項目だけを保存。
- robots: https://www.njpw.co.jp/robots.txt は200、`User-agent: * / Allow: /`。https://app.njpw.co.jp/robots.txt は404。ホストごとに指令とレート制限を適用。
- 規約: https://www.njpw.co.jp/terms は有料「NJPWスマホサイト」の定義と無断蓄積等の禁止を含む。一般無料ページの事実値への適用範囲は未確認。有料サイト・認証機能は取得対象外。
- 著作権案内: https://www.njpw.co.jp/copyright は海賊版・商品や映像の著作権侵害への説明。一般事実項目の自動取得禁止は今回確認できず、再配布許諾も未確認。記事本文・映像・画像・カードは公開しない。
- 2007〜2024年は年選択JSONにあることだけ確認し、過去全大会の保存は未実行。UI参照JSONの変更時は失敗記録を残す。

## 全日本公式

- 起点: https://www.all-japan.co.jp/ 、結果一覧 https://www.all-japan.co.jp/match/ 。GET form `select[name=years]`、選択肢2024/2025/2026。
- 2025年: https://www.all-japan.co.jp/match/?years=2025 、`.wp-pagenavi a.nextpostslink[href]` の実リンクで5ページ。`section.cont__item a.cont__item__link` と子 `time.cont__item__date[datetime]` から発見。80大会、01-02〜12-31。
- 詳細例: https://www.all-japan.co.jp/match/4136/ 、https://www.all-japan.co.jp/match/5032/ 。`h3.match__title` と `table.match__contentInfo__table tr.match__contentInfo__list` のth/tdから開催日・開始時間・会場・観衆を取得。地域は大会名の明示的「東京・」等から判定。
- robots: https://www.all-japan.co.jp/robots.txt は200、`/wp/wp-admin/` をDisallow、`/match/` は対象外。再配布許諾とは別。
- 規約リンク・事実値の自動取得/再配布許諾は未確認。https://www.all-japan.co.jp/privacy/ は個人情報方針。
- 2024年一覧の最終頁まで少数調査し、最古確認は2024-04-11。2024年1〜3月は網羅を主張できず、2016〜2023年は現在の年選択肢なし。2024年本体のbackfillは未実行。
- 認証・有料・正式APIは使わず、通常HTTP＋HTMLで取得。

## 未実装

STARDOM、CAGEMATCH、prowrestlingdata、yurutameeeee は未実装・未収集。

## 実装時のライブラリ資料

- HTTPX: https://www.python-httpx.org/advanced/transports/ （transport retry だけでは429処理が不足するため自前の明示的制御）
- BeautifulSoup: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
- uv: https://docs.astral.sh/uv/guides/projects/
- dbt DuckDB adapter: https://github.com/duckdb/dbt-duckdb
- Actions: https://github.com/actions/checkout 、https://github.com/astral-sh/setup-uv 、https://github.com/actions/upload-artifact 。安定した既存majorを利用し、実行で互換性を検証する。
