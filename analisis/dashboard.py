"""
app.py
------
Dashboard interactivo (Dash + Plotly + Folium) para analizar restaurantes
en varios departamentos de Colombia.

Cómo ejecutar:
    1. pip install -r requirements.txt
    2. python dashboard.py
    3. Abrir http://127.0.0.1:8050 en el navegador

Estructura del dashboard (pestañas):
    - Resumen / Dispersión y Burbujas
    - Correlaciones (regresión)
    - Mapa geoespacial (Folium)
"""

import folium
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
from folium.plugins import MarkerCluster

# ----------------------------------------------------------------------
# 1. Carga de datos
# ----------------------------------------------------------------------
df = pd.read_csv("restaurantes_colombia.csv")

departamentos_disponibles = sorted(df["departamento"].unique())
categorias_disponibles = sorted(df["Categoría"].unique())

# ----------------------------------------------------------------------
# 2. Inicialización de la app
# ----------------------------------------------------------------------
app = Dash(__name__, title="Restaurantes Colombia - Dashboard")
server = app.server  # útil si luego se despliega con gunicorn

# ----------------------------------------------------------------------
# 3. Layout
# ----------------------------------------------------------------------
app.layout = html.Div(
    style={"fontFamily": "Segoe UI, Arial, sans-serif", "margin": "0 30px"},
    children=[
        html.H1(
            "🍽️ Análisis de Restaurantes en Colombia",
            style={"textAlign": "center", "marginTop": "20px"},
        ),
        html.P(
            "Explora patrones entre categoría gastronómica, calificación, precio "
            "y popularidad en distintos departamentos.",
            style={"textAlign": "center", "color": "#555"},
        ),

        # --- Panel de filtros ---
        html.Div(
            style={
                "display": "flex",
                "flexWrap": "wrap",
                "gap": "25px",
                "justifyContent": "center",
                "backgroundColor": "#f7f7f9",
                "padding": "18px",
                "borderRadius": "10px",
                "marginBottom": "20px",
            },
            children=[
                html.Div(
                    [
                        html.Label("Departamento(s):", style={"fontWeight": "bold"}),
                        dcc.Dropdown(
                            id="filtro-departamento",
                            options=[{"label": c, "value": c} for c in departamentos_disponibles],
                            value=["Bogotá"],
                            multi=True,
                            placeholder="Selecciona una o más departamentos",
                        ),
                    ],
                    style={"minWidth": "320px"},
                ),
                html.Div(
                    [
                        html.Label("Categoría(s) de comida:", style={"fontWeight": "bold"}),
                        dcc.Dropdown(
                            id="filtro-categoria",
                            options=[{"label": c, "value": c} for c in categorias_disponibles],
                            value=categorias_disponibles,
                            multi=True,
                            placeholder="Selecciona una o más categorías",
                        ),
                    ],
                    style={"minWidth": "320px"},
                ),
                html.Div(
                    [
                        html.Label("Rango de precio (USD):", style={"fontWeight": "bold"}),
                        dcc.RangeSlider(
                            id="filtro-precio",
                            min=int(df["Precio promedio (USD)"].min()),
                            max=int(df["Precio promedio (USD)"].max()),
                            value=[int(df["Precio promedio (USD)"].min()), int(df["Precio promedio (USD)"].max())],
                            tooltip={"placement": "bottom", "always_visible": False},
                            allowCross=False,
                        ),
                    ],
                    style={"minWidth": "320px", "flexGrow": 1},
                ),
            ],
        ),

        # --- Tarjetas resumen (KPIs) ---
        html.Div(id="kpi-cards", style={"display": "flex", "gap": "15px", "justifyContent": "center", "marginBottom": "25px"}),

        # --- Pestañas de navegación ---
        dcc.Tabs(
            id="tabs",
            value="tab-dispersión",
            children=[
                dcc.Tab(label="📊 Dispersión y Burbujas", value="tab-dispersión"),
                dcc.Tab(label="📈 Correlaciones", value="tab-correlaciones"),
                dcc.Tab(label="🗺️ Mapa geoespacial", value="tab-mapa"),
            ],
        ),
        html.Div(id="contenido-tab", style={"marginTop": "20px", "paddingBottom": "40px"}),
    ],
)


# ----------------------------------------------------------------------
# 4. Función auxiliar: aplicar filtros
# ----------------------------------------------------------------------
def filtrar_datos(departamentos, categorias, rango_precio):
    departamentos = departamentos or departamentos_disponibles
    categorias = categorias or categorias_disponibles
    dff = df[
        df["departamento"].isin(departamentos)
        & df["Categoría"].isin(categorias)
        & df["Precio promedio (USD)"].between(rango_precio[0], rango_precio[1])
    ]
    return dff


# ----------------------------------------------------------------------
# 5. Callback: tarjetas KPI
# ----------------------------------------------------------------------
@app.callback(
    Output("kpi-cards", "children"),
    Input("filtro-departamento", "value"),
    Input("filtro-categoria", "value"),
    Input("filtro-precio", "value"),
)
def actualizar_kpis(departamentos, categorias, rango_precio):
    dff = filtrar_datos(departamentos, categorias, rango_precio)

    def tarjeta(titulo, valor, color):
        return html.Div(
            [
                html.Div(titulo, style={"fontSize": "13px", "color": "#666"}),
                html.Div(valor, style={"fontSize": "24px", "fontWeight": "bold", "color": color}),
            ],
            style={
                "backgroundColor": "white",
                "border": "1px solid #eee",
                "borderRadius": "10px",
                "padding": "15px 25px",
                "boxShadow": "0 1px 4px rgba(0,0,0,0.08)",
                "textAlign": "center",
                "minWidth": "160px",
            },
        )

    if dff.empty:
        return [tarjeta("Sin resultados", "—", "#999")]

    return [
        tarjeta("Restaurantes", f"{len(dff):,}", "#2c3e50"),
        tarjeta("Calificación prom.", f"{dff['Calificación'].mean():.2f} ⭐", "#e67e22"),
        tarjeta("Precio promedio", f"${dff['Precio promedio (USD)'].mean():,.0f} COP", "#27ae60"),
        tarjeta("Reseñas totales", f"{dff['Número de reseñas'].sum():,}", "#2980b9"),
    ]


# ----------------------------------------------------------------------
# 6. Callback principal: renderizar contenido según pestaña activa
# ----------------------------------------------------------------------
@app.callback(
    Output("contenido-tab", "children"),
    Input("tabs", "value"),
    Input("filtro-departamento", "value"),
    Input("filtro-categoria", "value"),
    Input("filtro-precio", "value"),
)
def renderizar_tab(tab, departamentos, categorias, rango_precio):
    dff = filtrar_datos(departamentos, categorias, rango_precio)

    if dff.empty:
        return html.Div(
            "No hay restaurantes que coincidan con los filtros seleccionados.",
            style={"textAlign": "center", "color": "#999", "padding": "40px"},
        )

    # ------------------------------------------------------------------
    # PESTAÑA 1: Dispersión y burbujas
    # ------------------------------------------------------------------
    if tab == "tab-dispersión":
        fig_burbujas = px.scatter(
            dff,
            x="Calificación",
            y="Precio promedio (USD)",
            size="Número de reseñas",
            color="Categoría",
            hover_name="Nombre",
            hover_data={"departamento": True, "Número de reseñas": True},
            size_max=45,
            title="Calificación vs. Precio promedio (tamaño = número de reseñas)",
            labels={
                "Calificación": "Calificación",
                "Precio promedio (USD)": "Precio promedio (USD)",
                "Categoría": "Categoría",
            },
        )
        fig_burbujas.update_layout(height=550, legend_title_text="Categoría")

        # Popularidad por categoría (promedio de reseñas)
        resumen_categoria = (
            dff.groupby("Categoría")
            .agg(num_resenas=("Número de reseñas", "mean"),
                  calificacion=("Calificación", "mean"), 
                  n=("Categoría", "count"))
            .reset_index()
            .sort_values("num_resenas", ascending=False)
        )
        fig_popularidad = px.bar(
            resumen_categoria,
            x="Categoría",
            y="num_resenas",
            color="calificacion",
            color_continuous_scale="Oranges",
            title="Popularidad promedio (reseñas) por categoría gastronómica",
            labels={"num_resenas": "Reseñas promedio", "categoria": "Categoría", "calificacion": "Calif. prom."},
        )
        fig_popularidad.update_layout(height=450, xaxis_tickangle=-30)

        # Precio promedio por departamento y categoría (mapa de calor tipo tabla)
        pivot_precio = dff.pivot_table(
            index="Categoría", columns="departamento", values="Precio promedio (USD)", aggfunc="mean"
        )
        fig_heatmap = px.imshow(
            pivot_precio,
            text_auto=".0f",
            color_continuous_scale="YlGnBu",
            aspect="auto",
            title="Precio promedio por categoría y departamento (USD)",
            labels={"color": "Precio prom."},
        )
        fig_heatmap.update_layout(height=500)

        return html.Div(
            [
                dcc.Graph(figure=fig_burbujas),
                html.Div(
                    [
                        html.Div(dcc.Graph(figure=fig_popularidad), style={"flex": "1", "minWidth": "45%"}),
                        html.Div(dcc.Graph(figure=fig_heatmap), style={"flex": "1", "minWidth": "45%"}),
                    ],
                    style={"display": "flex", "flexWrap": "wrap", "gap": "10px"},
                ),
            ]
        )

    # ------------------------------------------------------------------
    # PESTAÑA 2: Correlaciones (regresión)
    # ------------------------------------------------------------------
    elif tab == "tab-correlaciones":
        fig_reg_precio_calif = px.scatter(
            dff,
            x="Calificación",
            y="Precio promedio (USD)",
            color="departamento",
            trendline="ols",
            trendline_scope="overall",
            title="Regresión: Calificación vs. Precio promedio",
            labels={"Calificación": "Calificación", "Precio promedio (USD)": "Precio promedio (USD)"},
            opacity=0.55,
        )
        fig_reg_precio_calif.update_layout(height=500)

        fig_reg_resenas_calif = px.scatter(
            dff,
            x="Calificación",
            y="Número de reseñas",
            color="Categoría",
            trendline="ols",
            trendline_scope="overall",
            title="Regresión: Calificación vs. Número de reseñas",
            labels={"Calificación": "Calificación", "Número de reseñas": "Número de reseñas"},
            opacity=0.55,
        )
        fig_reg_resenas_calif.update_layout(height=500)

        fig_reg_precio_resenas = px.scatter(
            dff,
            x="Número de reseñas",
            y="Precio promedio (USD)",
            color="departamento",
            trendline="ols",
            trendline_scope="overall",
            title="Regresión: Número de reseñas vs. Precio promedio",
            labels={"Número de reseñas": "Número de reseñas", "Precio promedio (USD)": "Precio promedio (USD)"},
            opacity=0.55,
        )
        fig_reg_precio_resenas.update_layout(height=500)

        # Matriz de correlación numérica
        corr = dff[["Calificación", "Precio promedio (USD)", "Número de reseñas"]].corr().round(2)
        fig_corr = px.imshow(
            corr,
            text_auto=True,
            color_continuous_scale="RdBu_r",
            zmin=-1,
            zmax=1,
            title="Matriz de correlación entre variables numéricas",
        )
        fig_corr.update_layout(height=420)

        return html.Div(
            [
                html.Div(dcc.Graph(figure=fig_corr), style={"maxWidth": "600px", "margin": "0 auto"}),
                dcc.Graph(figure=fig_reg_precio_calif),
                dcc.Graph(figure=fig_reg_resenas_calif),
                dcc.Graph(figure=fig_reg_precio_resenas),
            ]
        )

    # ------------------------------------------------------------------
    # PESTAÑA 3: Mapa geoespacial (Folium)
    # ------------------------------------------------------------------
    elif tab == "tab-mapa":
        centro_lat = dff["Latitud"].mean()
        centro_lon = dff["Longitud"].mean()

        mapa = folium.Map(location=[centro_lat, centro_lon], zoom_start=6, tiles="OpenStreetMap")
        cluster = MarkerCluster().add_to(mapa)

        # Paleta simple por categoría
        paleta = px.colors.qualitative.Set3
        color_por_categoria = {
            cat: paleta[i % len(paleta)] for i, cat in enumerate(categorias_disponibles)
        }

        for _, fila in dff.iterrows():
            color = color_por_categoria.get(fila["Categoría"], "#3388ff")
            popup_html = (
                f"<b>{fila['Nombre']}</b><br>"
                f"Departamento: {fila['departamento']}<br>"
                f"Categoría: {fila['Categoría']}<br>"
                f"Calificación: {fila['Calificación']} ⭐<br>"
                f"Precio: ${fila['Precio promedio (USD)']:,.0f} COP<br>"
                f"Reseñas: {fila['Número de reseñas']}"
            )
            folium.CircleMarker(
                location=[fila["Latitud"], fila["Longitud"]],
                radius=5,
                color=color,
                fill=True,
                fill_opacity=0.8,
                popup=folium.Popup(popup_html, max_width=250),
            ).add_to(cluster)

        mapa_html = mapa._repr_html_()

        return html.Div(
            [
                html.P(
                    f"Mostrando {len(dff):,} restaurantes en el mapa. "
                    "Haz clic en un punto para ver el detalle.",
                    style={"textAlign": "center", "color": "#555"},
                ),
                html.Iframe(
                    srcDoc=mapa_html,
                    style={"width": "100%", "height": "650px", "border": "none", "borderRadius": "10px"},
                ),
            ]
        )

    return html.Div("Selecciona una pestaña.")


# ----------------------------------------------------------------------
# 7. Ejecutar la app
# ----------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, port=8050)
