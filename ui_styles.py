"""画面の見た目を1か所にまとめる。

色や余白の値をここだけに書くことで、画面のどこを直しても同じ見た目になる。
マーカーの色と凡例の色がずれないよう、Python側の定数からCSSを組み立てる。

CSSの入れ先は2つある。混同しないこと。
- `PAGE_STYLES`  : Streamlitのページに入れる。`st.markdown(..., unsafe_allow_html=True)`
- 地図の中のCSS : `st_folium`は地図をiframeに描くため、ページ側のCSSは届かない。
                  地図オブジェクトのヘッダーへ入れる（U-007で実装する）
"""

from __future__ import annotations

import json
from html import escape


# 指示書「Light / Nature」パレット。
COLORS = {
    "bg": "#F6F7F4",
    "surface": "#FFFFFF",
    "surface-muted": "#F0F2EE",
    "text-primary": "#17201A",
    "text-secondary": "#657068",
    "border": "#DDE2DB",
    # 操作部品（入力欄やボタン）の枠は、面との差を3.0以上にする必要がある。
    # `--border`は1.31しかないので、区切り線専用にして枠には使わない。
    "border-strong": "#809378",
    "brand": "#315B45",
    "brand-hover": "#274B39",
}

# 目撃からの経過日数を表す色。危険度ではない。
# 区分の境目はU-009で決める。ここでは色だけを持つ。
#
# `mid`は指示書の`#D99A3D`から暗くしてある。元の値だと中の白い足跡との差が
# 2.43しかなく、指示書§18が求めるコントラストを満たせなかった。
# 色相は変えず、明度だけを下げて3.44にしている。
TONE_COLORS = {
    "recent": "#D95D39",
    "mid": "#BA7E24",
    "older": "#6F8065",
    "oldest": "#69727D",
}

RADIUS = {
    "sm": "8px",
    "md": "12px",
    "lg": "16px",
}

SPACE = {
    "1": "4px",
    "2": "8px",
    "3": "12px",
    "4": "16px",
    "5": "24px",
    "6": "32px",
}

SHADOW = {
    "sm": "0 1px 3px rgb(0 0 0 / .08)",
    "md": "0 8px 24px rgb(0 0 0 / .12)",
}

FONT_STACK = '"Noto Sans JP", "Hiragino Sans", "Yu Gothic UI", sans-serif'

SIDEBAR_WIDTH = "300px"
SIDEBAR_WIDTH_TABLET = "260px"

# 画面幅の区切り。指示書§17に合わせる。
BREAKPOINT_TABLET = 1023
BREAKPOINT_MOBILE = 767

# 地図の高さ。`st_folium`はピクセルでしか指定できないため固定値にする。
# CSSでviewport全高に伸ばすとLeafletが自分の大きさを測り直せず、タイルが欠ける。
MAP_HEIGHT = 620

# 市町村を選んだときの寄せすぎの上限。
# 目撃1件だと表示範囲が点になり、上限がないと限界まで拡大してしまう。
FIT_MAX_ZOOM = 13
FIT_PADDING = (30, 30)

# 地図のベースタイル。OpenStreetMap標準は情報量と彩度が高く、ピンが埋もれる。
# 淡い地図に変えて、目撃地点を主役にする。
# foliumに同梱の指定で、attributionも自動で付く。追加インストールは不要。
MAP_TILES = "CartoDB positron"

# ヘッダーのアイコン。emojiではなく図形で描く。色はブランド色を継ぐ。
PAW_SVG = (
    '<svg class="app-header__paw" width="26" height="26" viewBox="0 0 26 26"'
    ' role="img" aria-label="クマの足跡">'
    '<ellipse cx="13" cy="17.2" rx="6.1" ry="5.1"/>'
    '<ellipse cx="5.9" cy="10.6" rx="2.6" ry="3.2"/>'
    '<ellipse cx="10.4" cy="6.9" rx="2.6" ry="3.4"/>'
    '<ellipse cx="15.6" cy="6.9" rx="2.6" ry="3.4"/>'
    '<ellipse cx="20.1" cy="10.6" rx="2.6" ry="3.2"/>'
    "</svg>"
)


def header_brand_html(title: str) -> str:
    """ヘッダー左側。足跡とタイトルを1行に並べる。"""

    return (
        f'<div class="app-header__brand">{PAW_SVG}'
        f'<h1 class="app-header__title">{title}</h1></div>'
    )


def header_meta_html(updated_label: str) -> str:
    """ヘッダー右側。データの最終更新日を出す。"""

    return f'<div class="app-header__meta">{updated_label} 更新</div>'


MARKER_SIZE = (36, 42)
MARKER_CLASS = "bear-marker"

# ピンの既定色。U-011で目撃からの経過日数に応じた色へ差し替える。
# それまでは新しさの意味を持たせないため、ブランド色を使う。
MARKER_DEFAULT_COLOR = COLORS["brand"]


def bear_marker_svg(fill_color: str = MARKER_DEFAULT_COLOR) -> str:
    """地図のピン。涙型の中に足跡を入れる。

    画像を読み込まないので、CDNのリンク切れが起きない。
    emojiは使わない。色は呼び出し側から渡す。
    """

    width, height = MARKER_SIZE

    return (
        f'<svg class="{MARKER_CLASS}__svg" width="{width}" height="{height}"'
        f' viewBox="0 0 {width} {height}" aria-hidden="true">'
        '<path d="M18 1C8.6 1 1 8.6 1 18c0 12.2 17 23 17 23s17-10.8 17-23C35 8.6 27.4 1 18 1z"'
        f' fill="{fill_color}" stroke="rgba(255,255,255,.9)" stroke-width="2"/>'
        '<g fill="rgba(255,255,255,.95)">'
        '<ellipse cx="18" cy="21" rx="4.6" ry="3.8"/>'
        '<ellipse cx="12.6" cy="16.4" rx="2" ry="2.5"/>'
        '<ellipse cx="16" cy="13.6" rx="2" ry="2.6"/>'
        '<ellipse cx="20" cy="13.6" rx="2" ry="2.6"/>'
        '<ellipse cx="23.4" cy="16.4" rx="2" ry="2.5"/>'
        "</g></svg>"
    )


CLUSTER_CLASS = "bear-cluster"

# クラスタの大きさの区切りと直径。色は件数で変えない（指示書§10）。
CLUSTER_TIERS = (
    ("small", 10, 38),
    ("medium", 50, 46),
    ("large", None, 54),
)

CLUSTER_OPTIONS = {
    # 重なった地点を開くための動き。どちらもLeafletの既定だが、意図として明示しておく。
    "zoomToBoundsOnClick": True,
    "spiderfyOnMaxZoom": True,
    # ホバーで範囲の多角形を出す既定の動きは、地図が騒がしくなるので切る。
    "showCoverageOnHover": False,
    "maxClusterRadius": 60,
}


def cluster_icon_js() -> str:
    """クラスタの見た目を作るJavaScript。件数で大きさだけを変える。

    Leaflet.markerclusterの既定は緑・黄・赤の丸で、件数が多いほど赤くなる。
    それでは「多い＝危険」に見えてしまうため、色は変えずに大きさだけを変える。
    """

    small_max, medium_max = CLUSTER_TIERS[0][1], CLUSTER_TIERS[1][1]
    small_px, medium_px, large_px = (tier[2] for tier in CLUSTER_TIERS)

    return f"""
function (cluster) {{
  var count = cluster.getChildCount();
  var tier = count < {small_max} ? "small" : (count < {medium_max} ? "medium" : "large");
  var px = count < {small_max} ? {small_px} : (count < {medium_max} ? {medium_px} : {large_px});
  return L.divIcon({{
    html: '<div class="{CLUSTER_CLASS} {CLUSTER_CLASS}--' + tier + '">' + count + '</div>',
    className: "{CLUSTER_CLASS}-wrapper",
    iconSize: L.point(px, px)
  }});
}}
"""


POPUP_CLASS = "pin-card"
POPUP_MAX_WIDTH = 320


def popup_card_html(
    municipality: str,
    details: list[tuple[str, str]],
    source_label: str,
    recency_label: str = "",
) -> str:
    """ピンをクリックしたときのカード。

    目撃データは自由記述なので必ずエスケープする。
    項目の並びは指示書§11に合わせ、日時・市町村・場所・内容・情報ソースの順にする。
    `recency_label`には「2日前」を渡す。色が読めなくても経過が分かるようにする。
    """

    value = dict(details)

    when = " ".join(
        part for part in (value.get("日付", ""), value.get("時間", "")) if part
    )
    recency = (
        f'<span class="{POPUP_CLASS}__recency">{escape(recency_label)}</span>'
        if recency_label
        else ""
    )

    return (
        f'<div class="{POPUP_CLASS}">'
        f'<div class="{POPUP_CLASS}__when">{escape(when)}{recency}</div>'
        f'<div class="{POPUP_CLASS}__title">{escape(municipality)}</div>'
        f'<div class="{POPUP_CLASS}__place">{escape(value.get("場所", ""))}</div>'
        f'<p class="{POPUP_CLASS}__body">{escape(value.get("状況", ""))}</p>'
        f'<div class="{POPUP_CLASS}__harm">人身被害　{escape(value.get("人身被害", ""))}</div>'
        f'<div class="{POPUP_CLASS}__source">{escape(source_label)}</div>'
        "</div>"
    )


ZOOM_CONTROL_POSITION = "bottomright"
HOME_LABEL = "山梨全体へ戻る"

LIST_CLASS = "sight-list"
LIST_OPEN_CLASS = f"{LIST_CLASS}--open"
LIST_EMPTY_TEXT = "この条件に合う目撃はありません。"


def _sighting_row_html(row: dict[str, object]) -> str:
    """一覧の1行。押せるようにボタンにする。

    `data-index`は地図のピンと結びつけるための番号。
    整数に変換してから埋め込む。文字列のまま入れると属性を抜け出せてしまう。
    """

    tone = str(row["tone"])

    return (
        "<li>"
        f'<button type="button" class="{LIST_CLASS}__row"'
        f' data-index="{int(row["index"])}">'
        f'<span class="{LIST_CLASS}__dot" aria-hidden="true"'
        f' style="background:{TONE_COLORS[tone]}"></span>'
        f'<span class="{LIST_CLASS}__when">{escape(str(row["date"]))}'
        f'<span class="{LIST_CLASS}__ago">{escape(str(row["recency"]))}</span>'
        "</span>"
        f'<span class="{LIST_CLASS}__where">'
        f'<span class="{LIST_CLASS}__city">{escape(str(row["municipality"]))}</span>'
        f'<span class="{LIST_CLASS}__place">{escape(str(row["place"]))}</span>'
        "</span></button></li>"
    )


def sighting_list_html(rows: list[dict[str, object]]) -> str:
    """地図に出ている目撃の一覧。

    件数は`rows`の長さから数える。渡された分は必ず全部並べる。
    別々に受け取ると「156件」と出しながら50件しか並んでいない、
    という食い違いが起こりうるため。

    `rows`の各要素は index / date / recency / municipality / place / tone を持つ。
    並び順は呼び出し側で決める（`sort_by_date_desc`）。
    """

    if not rows:
        body = f'<p class="{LIST_CLASS}__empty">{escape(LIST_EMPTY_TEXT)}</p>'
    else:
        items = "".join(_sighting_row_html(row) for row in rows)
        body = f'<ol class="{LIST_CLASS}__items">{items}</ol>'

    return (
        f'<div class="{LIST_CLASS} {LIST_OPEN_CLASS}">'
        f'<button type="button" class="{LIST_CLASS}__head"'
        f' aria-expanded="true" aria-controls="{LIST_CLASS}-body">'
        f'<span class="{LIST_CLASS}__title">目撃 {len(rows)}件</span>'
        f'<span class="{LIST_CLASS}__caret" aria-hidden="true"></span>'
        "</button>"
        f'<div class="{LIST_CLASS}__body" id="{LIST_CLASS}-body">{body}</div>'
        "</div>"
    )


def js_text(value: str) -> str:
    """Pythonの文字列をJavaScriptの文字列にする。

    市町村名などをそのまま埋め込むと、引用符でJavaScriptが壊れる。
    `ensure_ascii=False`にしないと日本語が`\\uXXXX`になって読めなくなる。
    """

    return json.dumps(value, ensure_ascii=False)


def chips_html(chips: list[str]) -> str:
    """地図の左上に出す、絞り込みの状態のチップ。

    「×」は付けない。地図はiframeの中にあり、そこからStreamlitの選択状態を
    変えられないため、押せないボタンを見せない。
    絞り込みの解除は、地図の外にあるボタンで行う。
    """

    return "".join(f'<span class="map-chip">{escape(chip)}</span>' for chip in chips)


def map_styles() -> str:
    """地図の中（iframe内）へ入れるCSS。

    `st.markdown`で入れたCSSはiframeを越えられないため、
    地図オブジェクトのヘッダーへ直接入れる。ピンのhoverやPopupの見た目はこちら。
    """

    return f"""<style>
.{MARKER_CLASS} {{
  background: transparent;
  border: 0;
}}

.{MARKER_CLASS}__svg {{
  display: block;
  filter: drop-shadow(0 3px 8px rgb(0 0 0 / 0.25));
  transform-origin: 50% 95%;
  transition: transform .12s ease-out;
}}

.{MARKER_CLASS}:hover .{MARKER_CLASS}__svg,
.{MARKER_CLASS}:focus-visible .{MARKER_CLASS}__svg {{
  transform: scale(1.11);
}}

.leaflet-marker-icon:focus-visible {{
  outline: 2px solid {COLORS["brand"]};
  outline-offset: 2px;
}}

/* クラスタ。ピンと同じデザイン言語にそろえる。 */
.{CLUSTER_CLASS}-wrapper {{
  background: transparent;
  border: 0;
}}

.{CLUSTER_CLASS} {{
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: {COLORS["brand"]};
  color: #FFFFFF;
  border: 2px solid rgba(255,255,255,.9);
  font-family: {FONT_STACK};
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  filter: drop-shadow(0 3px 8px rgb(0 0 0 / 0.25));
  transition: transform .12s ease-out;
}}

.{CLUSTER_CLASS}--small {{ font-size: 13px; }}
.{CLUSTER_CLASS}--medium {{ font-size: 15px; }}
.{CLUSTER_CLASS}--large {{ font-size: 17px; }}

.{CLUSTER_CLASS}-wrapper:hover .{CLUSTER_CLASS} {{
  transform: scale(1.08);
}}

/* Popup。Leaflet既定の見た目を全面的に上書きしてカードにする。 */
.leaflet-popup-content-wrapper {{
  background: {COLORS["surface"]};
  border-radius: {RADIUS["lg"]};
  box-shadow: {SHADOW["md"]};
  padding: 0;
}}

.leaflet-popup-content {{
  margin: 0;
  min-width: 260px;
  max-width: {POPUP_MAX_WIDTH}px;
  line-height: 1.6;
}}

.leaflet-popup-tip {{
  width: 12px;
  height: 12px;
  margin: -6px auto 0;
  box-shadow: none;
  background: {COLORS["surface"]};
}}

/* 閉じるボタンはタップ領域を44px確保する（指示書§18）。 */
.leaflet-popup-close-button {{
  width: 44px !important;
  height: 44px !important;
  font-size: 20px !important;
  line-height: 40px !important;
  color: {COLORS["text-secondary"]} !important;
  padding: 0 !important;
}}

.leaflet-popup-close-button:hover {{
  color: {COLORS["text-primary"]} !important;
  background: transparent;
}}

.{POPUP_CLASS} {{
  font-family: {FONT_STACK};
  color: {COLORS["text-primary"]};
  padding: {SPACE["4"]} {SPACE["4"]} {SPACE["3"]};
}}

.{POPUP_CLASS}__when {{
  font-size: 12px;
  color: {COLORS["text-secondary"]};
  font-variant-numeric: tabular-nums;
  padding-right: {SPACE["6"]};
}}

.{POPUP_CLASS}__recency {{
  margin-left: {SPACE["2"]};
  padding: 1px 6px;
  border-radius: {RADIUS["sm"]};
  background: {COLORS["surface-muted"]};
  color: {COLORS["text-primary"]};
  font-size: 11px;
  font-weight: 700;
}}

.{POPUP_CLASS}__title {{
  font-size: 16px;
  font-weight: 700;
  margin-top: {SPACE["1"]};
}}

.{POPUP_CLASS}__place {{
  font-size: 13px;
  color: {COLORS["text-secondary"]};
}}

.{POPUP_CLASS}__body {{
  font-size: 13px;
  margin: {SPACE["3"]} 0 0 0;
  overflow-wrap: anywhere;
}}

.{POPUP_CLASS}__harm {{
  font-size: 12px;
  color: {COLORS["text-secondary"]};
  margin-top: {SPACE["3"]};
  padding-top: {SPACE["2"]};
  border-top: 1px solid {COLORS["border"]};
}}

.{POPUP_CLASS}__source {{
  font-size: 11px;
  color: {COLORS["text-secondary"]};
  margin-top: {SPACE["1"]};
}}

/* 地図の上のチップ。いま何で絞り込んでいるかを地図を見たまま把握できるようにする。 */
.map-chips {{
  display: flex;
  flex-wrap: wrap;
  gap: {SPACE["2"]};
  margin: {SPACE["2"]} 0 0 {SPACE["2"]};
}}

.map-chip {{
  background: rgba(255,255,255,.94);
  color: {COLORS["text-primary"]};
  font-family: {FONT_STACK};
  font-size: 12px;
  font-weight: 700;
  padding: 6px 10px;
  border-radius: 999px;
  box-shadow: {SHADOW["sm"]};
  white-space: nowrap;
}}

/* 県全体へ戻るボタン。ズームボタンと同じ列に並べる。 */
.map-home a {{
  width: auto !important;
  padding: 0 10px;
  font-family: {FONT_STACK};
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}}

/* 目撃の一覧。地図の中に置くので、CSSもここに入れる。 */
.{LIST_CLASS}-wrapper {{
  background: transparent;
  border: 0;
}}

.{LIST_CLASS} {{
  width: 288px;
  max-width: 78vw;
  background: {COLORS["surface"]};
  border-radius: {RADIUS["lg"]};
  box-shadow: {SHADOW["md"]};
  font-family: {FONT_STACK};
  overflow: hidden;
  margin: {SPACE["2"]} {SPACE["2"]} 0 0;
}}

.{LIST_CLASS}__head {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: {SPACE["2"]};
  width: 100%;
  min-height: 44px;
  padding: 0 {SPACE["3"]};
  border: 0;
  background: {COLORS["surface"]};
  color: {COLORS["text-primary"]};
  cursor: pointer;
  text-align: left;
}}

.{LIST_CLASS}__title {{
  font-size: 13px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}}

/* 開閉の向きを三角形で示す。閉じているときは右向き。 */
.{LIST_CLASS}__caret {{
  width: 0;
  height: 0;
  border-left: 5px solid transparent;
  border-right: 5px solid transparent;
  border-top: 6px solid {COLORS["text-secondary"]};
  transition: transform .12s ease-out;
  transform: rotate(-90deg);
}}

.{LIST_OPEN_CLASS} .{LIST_CLASS}__caret {{
  transform: rotate(0deg);
}}

.{LIST_CLASS}__body {{
  display: none;
  border-top: 1px solid {COLORS["border"]};
}}

.{LIST_OPEN_CLASS} .{LIST_CLASS}__body {{
  display: block;
}}

.{LIST_CLASS}__items {{
  list-style: none;
  margin: 0;
  padding: 0;
  /* 地図の高さを超えないようにする。vhはiframeの高さに対する割合。 */
  max-height: min(380px, 58vh);
  overflow-y: auto;
}}

.{LIST_CLASS}__row {{
  display: flex;
  align-items: center;
  gap: {SPACE["2"]};
  width: 100%;
  min-height: 44px;
  padding: {SPACE["2"]} {SPACE["3"]};
  border: 0;
  border-bottom: 1px solid {COLORS["border"]};
  background: {COLORS["surface"]};
  color: {COLORS["text-primary"]};
  cursor: pointer;
  text-align: left;
  font-family: {FONT_STACK};
}}

.{LIST_CLASS}__row:hover {{
  background: {COLORS["surface-muted"]};
}}

/* キーボードで移動したとき、どこにいるかが分かるようにする。 */
.{LIST_CLASS}__row:focus-visible,
.{LIST_CLASS}__head:focus-visible {{
  outline: 2px solid {COLORS["brand"]};
  outline-offset: -2px;
}}

/* 開いた行に印を付ける。色以外の手がかりも残す。 */
.{LIST_CLASS}__row[aria-current="true"] {{
  background: {COLORS["surface-muted"]};
  box-shadow: inset 3px 0 0 {COLORS["brand"]};
}}

.{LIST_CLASS}__dot {{
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex: 0 0 auto;
  border: 1px solid rgba(0,0,0,.12);
}}

.{LIST_CLASS}__when {{
  flex: 0 0 auto;
  width: 74px;
  font-size: 12px;
  color: {COLORS["text-secondary"]};
  font-variant-numeric: tabular-nums;
}}

.{LIST_CLASS}__ago {{
  display: block;
  font-size: 11px;
}}

.{LIST_CLASS}__where {{
  flex: 1 1 auto;
  min-width: 0;
}}

.{LIST_CLASS}__city {{
  display: block;
  font-size: 13px;
  font-weight: 700;
}}

.{LIST_CLASS}__place {{
  display: block;
  font-size: 12px;
  color: {COLORS["text-secondary"]};
  overflow-wrap: anywhere;
}}

.{LIST_CLASS}__empty {{
  margin: 0;
  padding: {SPACE["4"]} {SPACE["3"]};
  font-size: 12px;
  color: {COLORS["text-secondary"]};
}}

/* ズームボタン。既定の浮いた見た目をやめ、他の要素とそろえる。 */
.leaflet-bar {{
  border: 0;
  border-radius: {RADIUS["md"]};
  box-shadow: {SHADOW["sm"]};
  overflow: hidden;
}}

/* ズームと「山梨全体へ戻る」。指で押せる44pxを確保する（指示書§18）。 */
.leaflet-bar a,
.leaflet-bar a:hover {{
  width: 44px;
  height: 44px;
  line-height: 44px;
  background: {COLORS["surface"]};
  color: {COLORS["text-primary"]};
  border-bottom: 1px solid {COLORS["border"]};
}}

.leaflet-bar a:hover {{
  background: {COLORS["surface-muted"]};
}}

.leaflet-bar a:last-child {{
  border-bottom: 0;
}}

.leaflet-control-attribution {{
  background: rgba(255,255,255,.85) !important;
  font-family: {FONT_STACK};
  font-size: 10px;
  color: {COLORS["text-secondary"]};
  border-radius: {RADIUS["sm"]} 0 0 0;
  padding: 2px 6px;
}}

.leaflet-control-attribution a {{
  color: {COLORS["text-secondary"]};
}}

@media (prefers-reduced-motion: reduce) {{
  .{MARKER_CLASS}__svg,
  .{CLUSTER_CLASS} {{
    transition: none;
  }}
}}
</style>"""


MAP_STYLES = map_styles()
CLUSTER_ICON_JS = cluster_icon_js()


def summary_html(
    count: int,
    period: tuple[str, str] | None,
    scope_label: str = "",
) -> str:
    """サイドバーの件数表示。数字だけを大きくし、期間は控えめに添える。

    `scope_label`には選んでいる期間（直近30日など）を渡す。
    どの条件での件数かが数字だけでは分からないため。
    """

    scope_line = (
        f'<div class="summary__scope">{escape(scope_label)}</div>' if scope_label else ""
    )
    period_line = (
        f'<div class="summary__period">収録期間 {escape(period[0])} 〜 {escape(period[1])}</div>'
        if period
        else ""
    )

    return (
        '<div class="summary">'
        '<div class="summary__label">地図に表示中</div>'
        f'<div class="summary__count">{count}<span class="summary__unit">件</span></div>'
        f"{scope_line}"
        f"{period_line}"
        "</div>"
    )


def legend_html(rows: list[tuple[str, str, int]]) -> str:
    """マーカーの色の意味を示す凡例。

    色だけに意味を持たせない（指示書§18）。丸の横に必ず言葉と件数を出す。
    `rows`は(区分名, 説明文, 件数)。
    """

    items = "".join(
        f'<div class="legend__row">'
        f'<span class="legend__dot" aria-hidden="true"'
        f' style="background:{TONE_COLORS[tone]}"></span>'
        f'<span class="legend__text">{escape(label)}</span>'
        f'<span class="legend__count">{count}</span>'
        "</div>"
        for tone, label, count in rows
    )

    return (
        '<div class="legend">'
        '<div class="legend__title">ピンの色は目撃からの経過</div>'
        f"{items}"
        '<div class="legend__note">危険度ではありません</div>'
        "</div>"
    )


DISCLAIMER_TITLE = "ご利用にあたって"

# 安全に関わる注意。折りたたみの中に隠さず、開かなくても読める場所に出す。
# 「この地図について」にも詳しい版を置くが、要点はここで必ず目に入るようにする。
DISCLAIMER_ITEMS = (
    "地図上の位置は、目撃地点のおおよその目安です。"
    "通学路の何メートル横か、といった精度の判断には使えません。",
    "1日1回の更新です。山梨県の公表より遅れます。"
    "緊急時や最新の情報は、山梨県や市町村の公式発表を確認してください。",
    "この情報に頼った結果について、作成者は責任を負いません。",
    "吹き出しの「状況」は、山梨県が公開しているデータの記述をそのまま掲載しています。"
    "個人や世帯を特定する目的では利用しないでください。",
)


def disclaimer_html(items: tuple[str, ...] = DISCLAIMER_ITEMS) -> str:
    """画面下に常時出す免責。開かなくても読める。"""

    lines = "".join(f"<li>{escape(item)}</li>" for item in items)

    return (
        '<div class="disclaimer">'
        f'<div class="disclaimer__title">{escape(DISCLAIMER_TITLE)}</div>'
        f'<ul class="disclaimer__items">{lines}</ul>'
        "</div>"
    )


# 画面を開いたときに通信する先。利用者のIPアドレスがこれらの相手に渡る。
# foliumが読み込むもので、こちらのコードで減らすのは難しい。
#
# ここに書いた一覧が実際とずれると、画面に書いてあることが嘘になる。
# `tests/test_external_hosts.py`が、実際に生成されるHTMLと突き合わせる。
EXTERNAL_HOSTS = (
    ("cdn.jsdelivr.net", "地図を描くプログラム（Leaflet など）"),
    ("cdnjs.cloudflare.com", "ピンをまとめる機能のプログラム"),
    ("code.jquery.com", "jQuery（Leaflet が使う）"),
    ("netdna.bootstrapcdn.com", "アイコン用のスタイル"),
    ("basemaps.cartocdn.com", "地図の画像。地図を動かすたびに読み込む"),
)

CONTACT_UNSET_TEXT = "連絡先は公開時に設定します（現在は未設定）。"

# アプリのサーバーが、最新データを読みに行く先（`remote_data.py`）。
# 上の`EXTERNAL_HOSTS`とは別に書く。あちらはブラウザが直接つなぐ相手で、
# 利用者のIPアドレスが渡る。こちらはサーバーがつなぐので、渡らない。
# 同じ一覧に混ぜると、利用者に渡る情報を実際より多く見せることになる。
SERVER_FETCH_HOST = "raw.githubusercontent.com"


def privacy_markdown(hosts: tuple[tuple[str, str], ...] = EXTERNAL_HOSTS) -> str:
    """プライバシーについての説明。

    集めていないことと、外部へ通信していることの両方を書く。
    「何も集めていません」だけだと、外部への通信を隠すことになる。
    """

    lines = "\n".join(f"    - `{host}` — {purpose}" for host, purpose in hosts)

    return (
        "**プライバシーについて**\n\n"
        "- 氏名や連絡先などを利用者から集めていません。入力欄もログインもありません\n"
        "- アクセス解析は入れていません\n"
        "- ただし画面を開くと、次の外部サーバーへ通信します。"
        "**利用者のIPアドレスとブラウザの情報が、これらの相手に渡ります**\n"
        f"{lines}\n"
        "- 画面に出すデータは、アプリのサーバーが"
        f"`{SERVER_FETCH_HOST}`（GitHub）から読み込みます。"
        "**これはサーバーからの通信です。利用者のブラウザは接続せず、"
        "利用者のIPアドレスがGitHubへ渡ることはありません**\n"
        "- 画面を配信している事業者が、接続の記録を保持する場合があります\n"
    )


def contact_markdown(url: str = "") -> str:
    """連絡先。未設定のときは、その旨をはっきり出す。"""

    if not url:
        destination = f"- {CONTACT_UNSET_TEXT}"
    else:
        destination = f"- GitHub の Issues: {url}"

    return (
        "**連絡先**\n\n"
        "誤りのご指摘や、掲載内容についてのご相談はこちらへお願いします。\n\n"
        f"{destination}\n\n"
        "掲載しているデータは山梨県が公開しているものです。"
        "元データそのものについては、山梨県 森林環境部 自然共生推進課へお問い合わせください。\n"
    )


def disclaimer_markdown(items: tuple[str, ...] = ()) -> str:
    """免責の詳しい版。画面下の要点と同じ内容に、出所の話を足す。"""

    lines = "\n".join(f"- {item}" for item in items)

    return (
        "**ご利用にあたって**\n\n"
        f"{lines}\n"
        "- このアプリは山梨県が作成したものではありません\n"
        "- 山梨県は、提供するデータの完全性や正確性を保証していません"
        "（山梨県オープンデータ利用規約）\n"
    )


def note_html(text: str) -> str:
    """控えめな注記。警告色は使わず、左の罫線だけで区別する。"""

    return f'<div class="note">{text}</div>'


def design_tokens_css() -> str:
    """CSS変数の定義を組み立てる。値はこのファイルの定数だけを使う。"""

    lines = [f"  --{name}: {value};" for name, value in COLORS.items()]
    lines += [f"  --tone-{name}: {value};" for name, value in TONE_COLORS.items()]
    lines += [f"  --radius-{name}: {value};" for name, value in RADIUS.items()]
    lines += [f"  --space-{name}: {value};" for name, value in SPACE.items()]
    lines += [f"  --shadow-{name}: {value};" for name, value in SHADOW.items()]

    return ":root {\n" + "\n".join(lines) + "\n}"


def page_styles() -> str:
    """Streamlitのページに入れるCSS。`unsafe_allow_html=True`で渡す。"""

    return f"""<style>
{design_tokens_css()}

/* 中央固定幅をやめる。地図をこの画面の主役にするため、横幅を余さず使う。 */
[data-testid="stMainBlockContainer"],
.block-container {{
  max-width: 100% !important;
  padding-top: var(--space-3) !important;
  padding-bottom: var(--space-4) !important;
  padding-left: var(--space-5) !important;
  padding-right: var(--space-5) !important;
}}

[data-testid="stAppViewContainer"] {{
  background: var(--bg);
}}

/* Streamlit既定のヘッダーは残す（サイドバーの開閉に必要）。背景だけ消す。 */
[data-testid="stHeader"] {{
  background: transparent;
}}

/* 文字色を指定する場所には、必ず背景も指定する。
   片方だけだと、テーマが変わったときに暗い背景へ暗い文字が乗って読めなくなる。 */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div,
[data-testid="stSidebarContent"],
[data-testid="stSidebarUserContent"] {{
  background: var(--surface);
  color: var(--text-primary);
}}

[data-testid="stSidebar"] {{
  border-right: 1px solid var(--border);
  width: {SIDEBAR_WIDTH} !important;
}}

[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{
  padding-top: var(--space-5);
}}

html, body, [data-testid="stAppViewContainer"] {{
  font-family: {FONT_STACK};
  color: var(--text-primary);
}}

/* 見出しは指示書のサイズに合わせる。巨大なH1は使わない。 */
h1 {{
  font-size: 22px !important;
  font-weight: 700 !important;
  letter-spacing: .01em;
}}

h2 {{
  font-size: 17px !important;
  font-weight: 700 !important;
}}

h3 {{
  font-size: 15px !important;
  font-weight: 700 !important;
}}

[data-testid="stCaptionContainer"] p {{
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.7;
}}

/* 地図をカードの中に閉じ込めず、画面の背景そのものとして扱う。 */
[data-testid="stIFrame"] {{
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  max-width: 100%;
}}

/* 長い語やURLが画面幅を押し広げないようにする。
   はみ出しを隠す指定で覆うのではなく、はみ出す原因のほうを直す。 */
[data-testid="stCaptionContainer"] p,
[data-testid="stSidebar"] .note {{
  overflow-wrap: anywhere;
}}

/* タブレット。地図を優先し、サイドバーを細くする。 */
@media (max-width: {BREAKPOINT_TABLET}px) {{
  [data-testid="stSidebar"] {{
    width: {SIDEBAR_WIDTH_TABLET} !important;
  }}
}}

/* スマートフォン。サイドバーは折りたたみで使う。 */
@media (max-width: {BREAKPOINT_MOBILE}px) {{
  [data-testid="stMainBlockContainer"],
  .block-container {{
    padding-left: var(--space-3) !important;
    padding-right: var(--space-3) !important;
  }}

  [data-testid="stSidebar"] {{
    width: 84vw !important;
    min-width: 0 !important;
  }}

  .app-header__title {{
    font-size: 19px !important;
  }}

  .app-header__meta {{
    text-align: left;
    padding-top: var(--space-2);
  }}

  .summary__count {{
    font-size: 28px;
  }}
}}

/* ヘッダー */
.app-header__brand {{
  display: flex;
  align-items: center;
  gap: var(--space-3);
  /* flexの子は既定で縮まない。狭い画面で外へはみ出さないようにする。 */
  min-width: 0;
}}

.app-header__paw {{
  fill: var(--brand);
  flex: 0 0 auto;
}}

.app-header__title {{
  font-size: 22px !important;
  font-weight: 700 !important;
  color: var(--text-primary);
  margin: 0 !important;
  padding: 0 !important;
  line-height: 1.3;
  min-width: 0;
  overflow-wrap: anywhere;
}}

.app-header__meta {{
  text-align: right;
  color: var(--text-secondary);
  font-size: 13px;
  font-variant-numeric: tabular-nums;
  padding-top: var(--space-1);
}}

.app-header__rule {{
  border: 0;
  border-top: 1px solid var(--border);
  margin: var(--space-3) 0 var(--space-4) 0;
}}

/* サイドバーの絞り込み欄。タップ領域を44px以上にする。 */
[data-testid="stSidebar"] label {{
  font-size: 12px !important;
  font-weight: 700 !important;
  color: var(--text-secondary) !important;
  letter-spacing: .04em;
}}

[data-testid="stSidebar"] [data-baseweb="select"] > div {{
  min-height: 44px;
  border-radius: var(--radius-md);
  border-color: var(--border-strong);
  background: var(--surface);
  color: var(--text-primary);
}}

/* 絞り込みを解除ボタン。背景と文字を対で指定する。 */
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {{
  background: var(--surface);
  color: var(--text-primary);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-md);
  min-height: 44px;
}}

[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:hover {{
  background: var(--surface-muted);
  color: var(--text-primary);
  border-color: var(--brand);
}}

/* 操作できるものは、キーボードでも位置が分かるようにする。 */
[data-testid="stSidebar"] button:focus-visible,
[data-testid="stSidebar"] [data-baseweb="select"] > div:focus-within,
[data-testid="stSidebar"] [role="radio"]:focus-visible,
a:focus-visible,
button:focus-visible {{
  outline: 2px solid var(--brand);
  outline-offset: 2px;
}}

/* 動きを減らす設定を尊重する（指示書§18）。 */
@media (prefers-reduced-motion: reduce) {{
  *,
  *::before,
  *::after {{
    animation-duration: .001ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: .001ms !important;
    scroll-behavior: auto !important;
  }}
}}

/* サイドバーの件数表示。数字だけを大きくする。 */
.summary {{
  margin: var(--space-5) 0 var(--space-4) 0;
  padding-top: var(--space-4);
  border-top: 1px solid var(--border);
}}

.summary__label {{
  font-size: 12px;
  font-weight: 700;
  letter-spacing: .04em;
  color: var(--text-secondary);
}}

.summary__count {{
  font-size: 32px;
  font-weight: 700;
  line-height: 1.2;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}}

.summary__unit {{
  font-size: 15px;
  font-weight: 700;
  margin-left: var(--space-1);
  color: var(--text-secondary);
}}

.summary__scope {{
  font-size: 13px;
  font-weight: 700;
  color: var(--brand);
}}

.summary__period {{
  font-size: 12px;
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
  margin-top: var(--space-1);
}}

/* 期間のラジオ。指で押せる大きさを確保する（指示書§18の44px）。 */
[data-testid="stSidebar"] [role="radiogroup"] label {{
  min-height: 44px;
  display: flex;
  align-items: center;
  padding: var(--space-1) 0;
  font-size: 14px !important;
  font-weight: 400 !important;
  color: var(--text-primary) !important;
  letter-spacing: normal;
}}

/* 凡例。色の意味を言葉でも示す。 */
.legend {{
  margin-top: var(--space-5);
  padding-top: var(--space-4);
  border-top: 1px solid var(--border);
}}

.legend__title {{
  font-size: 12px;
  font-weight: 700;
  letter-spacing: .04em;
  color: var(--text-secondary);
  margin-bottom: var(--space-2);
}}

.legend__row {{
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 26px;
  font-size: 13px;
}}

.legend__dot {{
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex: 0 0 auto;
  border: 1px solid rgba(0,0,0,.12);
}}

.legend__text {{
  flex: 1 1 auto;
  min-width: 0;
  color: var(--text-primary);
}}

.legend__count {{
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}}

.legend__note {{
  margin-top: var(--space-2);
  font-size: 11px;
  color: var(--text-secondary);
}}

/* 免責。地図の下に常時出す。読み飛ばされない程度に目立たせ、警告色は使わない。 */
.disclaimer {{
  margin-top: var(--space-5);
  padding: var(--space-4);
  background: var(--surface-muted);
  border-radius: var(--radius-md);
  border: 1px solid var(--border);
}}

.disclaimer__title {{
  font-size: 12px;
  font-weight: 700;
  letter-spacing: .04em;
  color: var(--text-primary);
  margin-bottom: var(--space-2);
}}

.disclaimer__items {{
  margin: 0;
  padding-left: 1.2em;
}}

.disclaimer__items li {{
  font-size: 12px;
  line-height: 1.8;
  color: var(--text-primary);
  overflow-wrap: anywhere;
}}

/* 注記。黄色の警告ボックスの代わりに使う。 */
.note {{
  margin-top: var(--space-3);
  padding: var(--space-2) 0 var(--space-2) var(--space-3);
  border-left: 3px solid var(--border);
  font-size: 12px;
  line-height: 1.7;
  color: var(--text-secondary);
}}
</style>"""


PAGE_STYLES = page_styles()
