from flask import Flask, request, render_template_string
import osmnx as ox
import folium
from pathlib import Path
import os

app = Flask(__name__)

# =========================================================
# ファイルパス
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

# suita_app.py と同じフォルダに置く
graph_path = BASE_DIR / "suita_drive.graphml"

print("吹田市の道路ネットワークを読み込んでいます...")

G = ox.io.load_graphml(graph_path)

print("道路ネットワークの読み込みが完了しました。")


# =========================================================
# HTML
# =========================================================

HTML = """
<!DOCTYPE html>
<html lang="ja">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>吹田市 最短経路検索</title>

<style>

body {
    font-family:
        "Yu Gothic",
        "Meiryo",
        sans-serif;

    margin: 0;
    background: #f5f5f5;
}

.container {
    width: 90%;
    max-width: 1100px;
    margin: 30px auto;
}

h1 {
    text-align: center;
}

.subtitle {
    text-align: center;
    color: #666666;
    margin-bottom: 25px;
}

.panel {
    background: white;
    padding: 25px;
    border-radius: 10px;
    margin-bottom: 20px;
}

.input-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
}

.point-box {
    border: 1px solid #cccccc;
    padding: 15px;
    border-radius: 8px;
}

label {
    display: block;
    margin-top: 10px;
}

input {
    width: 95%;
    padding: 9px;
    font-size: 16px;
}

button {
    display: block;
    margin: 25px auto 0;
    padding: 12px 35px;
    font-size: 17px;
    cursor: pointer;
}

.result {
    font-size: 22px;
    font-weight: bold;
    text-align: center;
    margin-bottom: 20px;
}

.map-container {
    width: 100%;
}

.error {
    color: #c00000;
    background: white;
    padding: 20px;
    text-align: center;
    border-radius: 10px;
}

@media (max-width: 700px) {

    .input-grid {
        grid-template-columns: 1fr;
    }

    .container {
        width: 95%;
    }
}

</style>

</head>


<body>

<div class="container">

<h1>吹田市 最短経路検索</h1>

<div class="subtitle">
OpenStreetMap道路ネットワークを用いた最短道路距離
</div>


<div class="panel">

<form method="POST">

<div class="input-grid">


<div class="point-box">

<h3>出発地点</h3>

<label>緯度</label>

<input
    type="number"
    step="any"
    name="start_lat"
    required
    value="{{ start_lat }}"
>

<label>経度</label>

<input
    type="number"
    step="any"
    name="start_lon"
    required
    value="{{ start_lon }}"
>

</div>


<div class="point-box">

<h3>目的地点</h3>

<label>緯度</label>

<input
    type="number"
    step="any"
    name="end_lat"
    required
    value="{{ end_lat }}"
>

<label>経度</label>

<input
    type="number"
    step="any"
    name="end_lon"
    required
    value="{{ end_lon }}"
>

</div>


</div>


<button type="submit">

最短経路を計算

</button>


</form>

</div>


{% if distance is not none %}

<div class="panel">

<div class="result">

最短道路距離：{{ distance }} km

</div>


<div class="map-container">

{{ map_html | safe }}

</div>

</div>

{% endif %}


{% if error %}

<div class="error">

{{ error }}

</div>

{% endif %}


</div>

</body>

</html>
"""


# =========================================================
# メイン画面
# =========================================================

@app.route("/", methods=["GET", "POST"])
def index():

    distance = None
    error = None
    map_html = None

    start_lat = ""
    start_lon = ""
    end_lat = ""
    end_lon = ""

    if request.method == "POST":

        try:

            # -------------------------------------------------
            # 入力値
            # -------------------------------------------------

            start_lat = float(
                request.form["start_lat"]
            )

            start_lon = float(
                request.form["start_lon"]
            )

            end_lat = float(
                request.form["end_lat"]
            )

            end_lon = float(
                request.form["end_lon"]
            )


            # -------------------------------------------------
            # 最寄り道路ノード
            # -------------------------------------------------

            start_node = ox.distance.nearest_nodes(
                G,
                X=start_lon,
                Y=start_lat
            )

            end_node = ox.distance.nearest_nodes(
                G,
                X=end_lon,
                Y=end_lat
            )


            # -------------------------------------------------
            # 最短道路距離で経路探索
            # -------------------------------------------------

            route = ox.routing.shortest_path(
                G,
                start_node,
                end_node,
                weight="length"
            )


            if route is None:

                raise Exception(
                    "経路を見つけることができませんでした。"
                )


            # -------------------------------------------------
            # 経路データ
            # -------------------------------------------------

            route_gdf = ox.routing.route_to_gdf(
                G,
                route,
                weight="length"
            )


            # -------------------------------------------------
            # 総道路距離
            # -------------------------------------------------

            distance = round(
                route_gdf["length"].sum() / 1000,
                3
            )


            # -------------------------------------------------
            # 地図
            # -------------------------------------------------

            center_lat = (
                start_lat + end_lat
            ) / 2

            center_lon = (
                start_lon + end_lon
            ) / 2


            m = folium.Map(
                location=[
                    center_lat,
                    center_lon
                ],
                zoom_start=14,
                tiles="OpenStreetMap"
            )


            # 出発地点

            folium.Marker(
                [
                    start_lat,
                    start_lon
                ],
                popup="出発地点",
                tooltip="出発地点"
            ).add_to(m)


            # 目的地点

            folium.Marker(
                [
                    end_lat,
                    end_lon
                ],
                popup="目的地点",
                tooltip="目的地点"
            ).add_to(m)


            # 最短経路

            folium.GeoJson(
                route_gdf.to_json(),
                name="最短経路",
                style_function=lambda feature: {
                    "weight": 6
                }
            ).add_to(m)


            # 経路全体を表示

            minx, miny, maxx, maxy = (
                route_gdf.total_bounds
            )

            m.fit_bounds(
                [
                    [miny, minx],
                    [maxy, maxx]
                ]
            )


            # HTMLファイルを書き出さず、
            # ページ内に地図を直接表示
            map_html = m._repr_html_()


        except Exception as e:

            error = str(e)


    return render_template_string(
        HTML,
        distance=distance,
        error=error,
        map_html=map_html,
        start_lat=start_lat,
        start_lon=start_lon,
        end_lat=end_lat,
        end_lon=end_lon
    )


# =========================================================
# ローカル実行用
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )