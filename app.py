"""山梨県のツキノワグマ目撃情報を、市町村ごとに地図で見る最小Streamlitアプリ。"""

# `int | None`のような書き方をPython 3.9でも使えるようにする。
# これがないと3.10以上でしか動かず、置く場所を選ぶことになる。
from __future__ import annotations

from collections import Counter
from pathlib import Path

import folium
import streamlit as st
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

from data_utils import (
    ALL_MUNICIPALITIES,
    PERIOD_ALL,
    PERIOD_CHOICES,
    PERIOD_SEASON,
    available_municipalities,
    coordinate_bounds,
    data_period,
    date_label,
    days_ago,
    days_ago_label,
    fetched_at,
    filter_by_municipality,
    filter_by_period,
    japanese_date,
    load_all_records,
    municipality_counts,
    municipality_label,
    reference_date,
    sighting_details,
    sighting_tone,
    sort_by_date_desc,
    split_by_coordinates,
    tone_ranges,
)
from map_overlays import MARKER_INDEX_OPTION, MapControls, SightingListControl
from ui_styles import (
    CLUSTER_ICON_JS,
    CLUSTER_OPTIONS,
    DISCLAIMER_ITEMS,
    FIT_MAX_ZOOM,
    FIT_PADDING,
    MAP_HEIGHT,
    MAP_STYLES,
    MAP_TILES,
    MARKER_CLASS,
    MARKER_SIZE,
    PAGE_STYLES,
    POPUP_MAX_WIDTH,
    TONE_COLORS,
    ZOOM_CONTROL_POSITION,
    bear_marker_svg,
    contact_markdown,
    disclaimer_html,
    disclaimer_markdown,
    header_brand_html,
    header_meta_html,
    legend_html,
    note_html,
    popup_card_html,
    privacy_markdown,
    sighting_list_html,
    summary_html,
)


APP_DIR = Path(__file__).resolve().parent
DATA_PATHS = [
    APP_DIR / "data" / "2026kumadata.csv",
    APP_DIR / "data" / "2026kumadata_new.csv",
]

# データを取得した日を書いたファイル。`scripts/fetch_data.py`が更新する。
FETCHED_AT_PATH = APP_DIR / "data" / "fetched_at.txt"
UNKNOWN_FETCHED_AT = "取得日不明"

# 県全体を映すときの中心と拡大率。市町村を選んだときは目撃地点の範囲へ寄せる。
YAMANASHI_CENTER = (35.66, 138.57)
YAMANASHI_ZOOM = 9

APP_TITLE = "山梨クマ目撃マップ"

# 期間の初期値。「今季」にしておくと、開いた直後は収録分がすべて見える。
# いきなり絞られていると、記録がないのか絞られているのか分からなくなる。
DEFAULT_PERIOD = PERIOD_SEASON

# 絞り込みを解除できるよう、ウィジェットに名前を付けておく。
PERIOD_KEY = "selected_period"
MUNICIPALITY_KEY = "selected_municipality"

# 連絡先。公開する前にGitHubのIssuesのURLを入れる。
# 空のままだと、画面に「未設定」と出る。
CONTACT_URL = "https://github.com/hroabe/yamanashi-bear-map/issues"

ABOUT_TEXT = "\n\n".join(
    [
        (
            "市町村と期間を選ぶと、ツキノワグマの目撃地点を地図で確認できます。\n"
            "ピンや一覧の行を押すと、日付・時間・場所・状況・人身被害の有無が読めます。"
        ),
        (
            "**このアプリで分からないこと**\n\n"
            "- 地図上の位置は目撃地点のおおよその目安です。"
            "元データに「大まかな付近を表示した目安」と明記されています\n"
            "- 座標がない目撃は地図に出せません。件数はサイドバーに出しています\n"
            "- 危険度の判定はしません。データに書かれていないことは表示しません"
        ),
        disclaimer_markdown(DISCLAIMER_ITEMS),
        privacy_markdown(),
        contact_markdown(CONTACT_URL),
    ]
)

DATASET_URL = "https://catalog.dataplatform-yamanashi.jp/dataset/kuma1"
TERMS_URL = "https://www.pref.yamanashi.jp/opendata/kiyaku.html"

def source_text(fetched_label: str) -> str:
    """画面下の出所表示。取得日はデータと一緒に記録した値を使う。

    山梨県オープンデータ利用規約は、加工して使う場合に「加工して作成」の明記を求めている。
    このアプリは市町村での絞り込みと表記ゆれの集約を行うため、加工にあたる。
    """

    return (
        "出典：山梨県 森林環境部 自然共生推進課"
        f"『ツキノワグマ出没・目撃情報（令和8年度／直近1か月）』"
        f"（[やまなしデータプラットフォーム]({DATASET_URL})・{fetched_label}取得）を加工して作成"
        f"／利用条件：[山梨県オープンデータ利用規約]({TERMS_URL})（CC BY 4.0互換）"
        "／このアプリは山梨県が作成したものではありません。"
    )

# 吹き出しの中に入れる短い出典。画面下の詳しい出所表示とは別に、
# カード単体を見ても情報源が分かるようにする（指示書§11の必須項目）。
POPUP_SOURCE_LABEL = "出典：山梨県 森林環境部 自然共生推進課"


st.set_page_config(
    page_title="山梨クマ目撃マップ",
    page_icon="🐻",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(PAGE_STYLES, unsafe_allow_html=True)


@st.cache_data
def get_records() -> list[dict[str, str]]:
    return load_all_records(DATA_PATHS)


def popup_html(record: dict[str, object], days: int | None) -> str:
    """吹き出しのカードを作る。エスケープは`popup_card_html`の中で行う。"""

    return popup_card_html(
        municipality_label(record),
        sighting_details(record),
        POPUP_SOURCE_LABEL,
        days_ago_label(days),
    )


def render_header(updated_label: str) -> None:
    """ヘッダー1行。左に足跡とタイトル、右に更新日と説明の折りたたみ。

    説明文は常時表示しない。指示書のとおり、必要な人だけが開く形にする。
    """

    brand, meta = st.columns([7, 3], vertical_alignment="center")
    with brand:
        st.markdown(header_brand_html(APP_TITLE), unsafe_allow_html=True)
    with meta:
        st.markdown(header_meta_html(updated_label), unsafe_allow_html=True)
        with st.popover("この地図について", width="stretch"):
            st.markdown(ABOUT_TEXT)

    st.markdown('<hr class="app-header__rule">', unsafe_allow_html=True)


# ヘッダーは、データを読んで更新日が分かってから描く。
# 読み込みに失敗したときもヘッダーを先に出したいので、場所だけ先に取っておく。
header_slot = st.container()

try:
    records = get_records()
except (OSError, ValueError) as error:
    with header_slot:
        render_header("―")
    st.error(f"データを読み込めませんでした: {error}")
    st.info("DATA.md と data/ のファイル名・列名を確認してください。")
    st.stop()

period = data_period(records)
reference = reference_date(records)

# 取得日はデータと一緒に記録した値から決める。読めなければ「取得日不明」と出す。
# 分からないのに日付を出すと、いつのデータかを誤って伝えることになる。
fetched = fetched_at(FETCHED_AT_PATH)
fetched_label = japanese_date(fetched) if fetched else UNKNOWN_FETCHED_AT

# プルダウンに並べる市町村は、期間を変えても増減させない。
# 選んでいた市町村が消えて選択が戻ってしまうのを避けるため。
municipalities = available_municipalities(records)

def clear_filters() -> None:
    """絞り込みを初期状態へ戻す。

    ボタンのコールバックで動かす。画面を描いた後にウィジェットの値を
    書き換えることはできないため、コールバックの中で行う必要がある。
    """

    st.session_state[PERIOD_KEY] = DEFAULT_PERIOD
    st.session_state[MUNICIPALITY_KEY] = ALL_MUNICIPALITIES


with st.sidebar:
    selected_period = st.radio(
        "期間",
        PERIOD_CHOICES,
        index=PERIOD_CHOICES.index(DEFAULT_PERIOD),
        key=PERIOD_KEY,
    )

in_period = filter_by_period(records, selected_period, reference)
counts = municipality_counts(in_period)
mappable, unmappable = split_by_coordinates(in_period)


def municipality_option_label(name: str) -> str:
    """プルダウンの表示。市町村名の後ろに、選んだ期間の目撃件数を添える。"""

    if name == ALL_MUNICIPALITIES:
        return f"すべての市町村　{len(in_period)}件"

    return f"{name}　{counts.get(name, 0)}件"


with st.sidebar:
    selected_municipality = st.selectbox(
        "市町村",
        [ALL_MUNICIPALITIES, *municipalities],
        format_func=municipality_option_label,
        key=MUNICIPALITY_KEY,
    )

    filtered = (
        selected_period != DEFAULT_PERIOD or selected_municipality != ALL_MUNICIPALITIES
    )
    st.button(
        "絞り込みを解除",
        on_click=clear_filters,
        disabled=not filtered,
        width="stretch",
    )

# 日付の新しい順に固定する。一覧とピンの追加順をそろえるため、ここで並べ替える。
results = sort_by_date_desc(filter_by_municipality(mappable, selected_municipality))
hidden = filter_by_municipality(unmappable, selected_municipality)

with header_slot:
    render_header(period[1] if period else "―")

with st.sidebar:
    st.markdown(
        summary_html(len(results), period, selected_period), unsafe_allow_html=True
    )
    if hidden:
        st.markdown(
            note_html(
                f"{len(hidden)}件は緯度・経度がないか山梨県の範囲から外れているため、"
                "地図に出していません。こちらで座標を補うことはしていません。"
            ),
            unsafe_allow_html=True,
        )
    counts_note = "プルダウンの件数は、選んだ期間の目撃の総数です。地図に出せないものも含みます。"
    if reference:
        counts_note += (
            f"期間は{japanese_date(reference)}"
            "（記録の中でいちばん新しい日）から数えています。"
        )
    st.markdown(note_html(counts_note), unsafe_allow_html=True)

    tone_counts = Counter(sighting_tone(days_ago(r, reference)) for r in results)
    st.markdown(
        legend_html([(tone, label, tone_counts[tone]) for tone, label in tone_ranges()]),
        unsafe_allow_html=True,
    )

if not results:
    conditions = f"「{selected_period}」「{selected_municipality}」"
    if hidden:
        st.info(
            f"{conditions}の目撃は記録されていますが、緯度・経度がないため地図に表示できません。"
            "期間を広げるか、別の市町村を選んでください。"
        )
    elif period:
        st.info(
            f"{conditions}に合う目撃の記録がありません。"
            f"このデータの収録期間は{period[0]}〜{period[1]}です。"
            "期間を「すべて」に広げるか、別の市町村を選んでください。"
        )
    else:
        st.info(f"{conditions}に合う目撃の記録がありません。条件を変えてください。")

bear_map = folium.Map(
    location=YAMANASHI_CENTER,
    zoom_start=YAMANASHI_ZOOM,
    tiles=MAP_TILES,
    # ホイールでのズームは切る。Leafletはホイールの累積量を必ず1段以上に丸めるため、
    # 感度を下げても、スクロールが判定区間をまたぐと複数段動いてしまう。
    # 拡大縮小は左上の+/-ボタンとダブルクリックで行う。
    scroll_wheel_zoom=False,
    zoom_snap=1,
    zoom_delta=1,
    zoom_control=ZOOM_CONTROL_POSITION,
)

# ピンのhoverなどのCSSは、地図の中へ入れないと効かない。
bear_map.get_root().header.add_child(folium.Element(MAP_STYLES))

# 密集した地点はまとめる。クリックで開く。
pins = MarkerCluster(
    icon_create_function=CLUSTER_ICON_JS,
    options=CLUSTER_OPTIONS,
).add_to(bear_map)

for index, record in enumerate(results):
    days = days_ago(record, reference)

    # 画像のピンは使わない。foliumの既定マーカーはLeafletの画像をCDNから読むが、
    # streamlit-foliumはiframe内に描くため画像の場所を解決できずリンク切れになる。
    marker = folium.Marker(
        location=[record["緯度数値"], record["経度数値"]],
        icon=folium.DivIcon(
            # 色は目撃からの経過日数を表す。危険度ではない。
            html=bear_marker_svg(TONE_COLORS[sighting_tone(days)]),
            icon_size=MARKER_SIZE,
            icon_anchor=(MARKER_SIZE[0] // 2, MARKER_SIZE[1] - 2),
            popup_anchor=(0, -MARKER_SIZE[1] + 4),
            class_name=MARKER_CLASS,
        ),
        # 色が読めない人にも伝わるよう、経過を言葉でも出す。
        tooltip=(
            f"{municipality_label(record)}　{date_label(record)}"
            f"（{days_ago_label(days)}）"
        ),
        popup=folium.Popup(
            folium.Html(popup_html(record, days), script=True),
            max_width=POPUP_MAX_WIDTH,
        ),
        # 一覧の行から探すための番号。変数名は`streamlit-folium`が付け替えるため、
        # 名前ではなくこの値でピンを見つける。
        **{MARKER_INDEX_OPTION: index},
    ).add_to(pins)

# 地図の上に、絞り込みの状態と県全体へ戻るボタンを置く。
# 地図の組み立てが終わってから足す。JavaScriptが地図の変数を参照するため。
chips = [f"目撃 {len(results)}件"]
if selected_period != PERIOD_ALL:
    chips.append(selected_period)
if selected_municipality != ALL_MUNICIPALITIES:
    chips.append(selected_municipality)

# 地図の子要素として足す。`get_root().script`へ足すと、
# `streamlit-folium`の組み立て対象から外れて画面に届かない。
bear_map.add_child(MapControls(chips, YAMANASHI_CENTER, YAMANASHI_ZOOM))

# 地図に出ている目撃の一覧。並びは`results`と同じなので、
# 行の`data-index`がそのままピンの番号になる（L-004で使う）。
list_rows = [
    {
        "index": index,
        "date": date_label(record),
        "recency": days_ago_label(days_ago(record, reference)),
        "municipality": municipality_label(record),
        "place": record["場所"],
        "tone": sighting_tone(days_ago(record, reference)),
    }
    for index, record in enumerate(results)
]
bear_map.add_child(SightingListControl(sighting_list_html(list_rows)))

# 市町村を選んだら、その目撃地点がちょうど収まる範囲へ寄せる。
# 平均の中心と固定の拡大率では、広い市町村で端が切れ、狭い市町村では余白が空く。
bounds = (
    coordinate_bounds(results)
    if selected_municipality != ALL_MUNICIPALITIES
    else None
)
if bounds:
    # 1件だけのときは範囲が点になる。上限を決めないと限界まで寄ってしまう。
    bear_map.fit_bounds(bounds, padding=FIT_PADDING, max_zoom=FIT_MAX_ZOOM)

st_folium(
    bear_map, height=MAP_HEIGHT, use_container_width=True, returned_objects=[]
)

st.caption("地図の拡大縮小は、右下の + − ボタンかダブルクリックで行えます。")

# 免責は開かなくても読める場所に出す。「この地図について」にも詳しい版を置くが、
# 安全に関わる注意を、開かないと読めない場所だけに置かない。
st.markdown(disclaimer_html(), unsafe_allow_html=True)

st.caption(source_text(fetched_label))
