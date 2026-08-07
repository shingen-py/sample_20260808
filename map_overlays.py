"""地図の上に置く操作を、foliumの部品として作る。

`streamlit-folium`は地図のHTMLをそのまま画面へ渡さない。
地図オブジェクトの子要素をたどってJavaScriptを組み立て直す。
そのため、`get_root().script`へ足したスクリプトは画面に届かない。

ここでは`MacroElement`を継承し、地図の子要素として足す。
こうすると組み立ての対象に入る。

もうひとつの決まり: マーカーを変数名で参照しない。
`streamlit-folium`は変数名を付け替えるため、名前を埋め込むと合わなくなる。
代わりに各マーカーへ`dataIndex`を持たせ、実行時に探す。
"""

from __future__ import annotations

from branca.element import MacroElement
from jinja2 import Template

from ui_styles import (
    BREAKPOINT_MOBILE,
    HOME_LABEL,
    LIST_CLASS,
    LIST_OPEN_CLASS,
    ZOOM_CONTROL_POSITION,
    chips_html,
    js_text,
)


MARKER_INDEX_OPTION = "dataIndex"


class MapControls(MacroElement):
    """左上に絞り込みの状態、右下に県全体へ戻るボタンを置く。"""

    _template = Template(
        """
        {% macro script(this, kwargs) %}
        (function () {
          var map = {{ this._parent.get_name() }};
          var Chips = L.Control.extend({
            options: {position: 'topleft'},
            onAdd: function () {
              var box = L.DomUtil.create('div', 'map-chips');
              box.innerHTML = {{ this.chips }};
              L.DomEvent.disableClickPropagation(box);
              return box;
            }
          });
          map.addControl(new Chips());

          var Home = L.Control.extend({
            options: {position: {{ this.position }}},
            onAdd: function () {
              var bar = L.DomUtil.create('div', 'leaflet-bar map-home');
              var link = L.DomUtil.create('a', '', bar);
              link.href = '#';
              link.title = {{ this.home_label }};
              link.innerHTML = {{ this.home_label }};
              L.DomEvent.on(link, 'click', L.DomEvent.stop);
              L.DomEvent.on(link, 'click', function () {
                map.setView([{{ this.latitude }}, {{ this.longitude }}], {{ this.zoom }});
              });
              return bar;
            }
          });
          map.addControl(new Home());
        })();
        {% endmacro %}
        """
    )

    def __init__(
        self,
        chips: list[str],
        center: tuple[float, float],
        zoom: int,
        home_label: str = HOME_LABEL,
    ):
        super().__init__()
        self._name = "MapControls"
        self.chips = js_text(chips_html(chips))
        self.latitude = float(center[0])
        self.longitude = float(center[1])
        self.zoom = int(zoom)
        self.home_label = js_text(home_label)
        self.position = js_text(ZOOM_CONTROL_POSITION)


class SightingListControl(MacroElement):
    """右上に目撃の一覧を置き、行と地図のピンを結びつける。

    一覧の上でのクリックとスクロールは地図へ伝えない。
    伝わると、行を押したつもりが地図が動いたり、
    一覧をスクロールしたつもりが地図がずれたりする。
    """

    _template = Template(
        """
        {% macro script(this, kwargs) %}
        (function () {
          var map = {{ this._parent.get_name() }};

          function findCluster() {
            var found = null;
            map.eachLayer(function (layer) {
              if (layer.zoomToShowLayer) { found = layer; }
            });
            return found;
          }

          function findMarker(cluster, index) {
            var layers = cluster ? cluster.getLayers() : [];
            for (var i = 0; i < layers.length; i++) {
              var options = layers[i].options || {};
              if (options.{{ this.index_option }} === index) { return layers[i]; }
            }
            var loose = null;
            map.eachLayer(function (layer) {
              var options = layer.options || {};
              if (options.{{ this.index_option }} === index) { loose = layer; }
            });
            return loose;
          }

          var List = L.Control.extend({
            options: {position: 'topright'},
            onAdd: function () {
              var box = L.DomUtil.create('div', '{{ this.wrapper_class }}');
              box.innerHTML = {{ this.list_html }};
              L.DomEvent.disableClickPropagation(box);
              L.DomEvent.disableScrollPropagation(box);

              var panel = box.querySelector('.{{ this.list_class }}');
              var head = box.querySelector('.{{ this.list_class }}__head');
              L.DomEvent.on(head, 'click', function () {
                var open = panel.classList.toggle('{{ this.open_class }}');
                head.setAttribute('aria-expanded', open ? 'true' : 'false');
              });

              // 画面が狭いときは閉じておく。開いたままだと地図が隠れてしまう。
              // 判定は地図の幅で行う。ページ全体の幅ではない。
              var width = map.getSize().x || window.innerWidth;
              if (width <= {{ this.mobile_breakpoint }}) {
                panel.classList.remove('{{ this.open_class }}');
                head.setAttribute('aria-expanded', 'false');
              }

              box.addEventListener('click', function (event) {
                var row = event.target.closest('.{{ this.list_class }}__row');
                if (!row) { return; }
                var index = Number(row.dataset.index);
                var cluster = findCluster();
                var marker = findMarker(cluster, index);
                if (!marker) { return; }

                panel.querySelectorAll('.{{ this.list_class }}__row').forEach(
                  function (other) { other.removeAttribute('aria-current'); }
                );
                row.setAttribute('aria-current', 'true');

                if (cluster && cluster.zoomToShowLayer) {
                  cluster.zoomToShowLayer(marker, function () { marker.openPopup(); });
                } else {
                  marker.openPopup();
                }
              });

              return box;
            }
          });
          map.addControl(new List());
        })();
        {% endmacro %}
        """
    )

    def __init__(self, list_html: str):
        super().__init__()
        self._name = "SightingListControl"
        self.list_html = js_text(list_html)
        self.list_class = LIST_CLASS
        self.open_class = LIST_OPEN_CLASS
        self.wrapper_class = f"{LIST_CLASS}-wrapper"
        self.index_option = MARKER_INDEX_OPTION
        self.mobile_breakpoint = BREAKPOINT_MOBILE
