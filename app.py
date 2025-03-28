from flask import Flask, render_template, request, jsonify
import pandas as pd

app = Flask(__name__)

# Cargar el CSV y limpiar los nombres de columna
df_promos = pd.read_csv("Promociones vigentes.csv")
df_promos.columns = [col.strip() for col in df_promos.columns]

# Aseguramos que la columna "Se requiere" exista
if "Se requiere" not in df_promos.columns:
    df_promos["Se requiere"] = "n/a"

def normalize_str(s):
    """Convierte s a cadena, elimina espacios y pasa a minúsculas."""
    return str(s).strip().lower()

def filter_promos(banco, rubro, establecimiento, dia):
    df_filtered = df_promos.copy()
    
    # Normalizar las columnas para filtrar
    df_filtered["Banco/Billetera"] = df_filtered["Banco/Billetera"].apply(normalize_str)
    df_filtered["Rubro"] = df_filtered["Rubro"].apply(normalize_str)
    df_filtered["Establecimiento"] = df_filtered["Establecimiento"].apply(normalize_str)
    df_filtered["Día de la promoción"] = df_filtered["Día de la promoción"].apply(normalize_str)
    
    if banco and banco.lower() != "todos":
        df_filtered = df_filtered[df_filtered["Banco/Billetera"].str.contains(normalize_str(banco), na=False)]
    if rubro and rubro.lower() != "todos":
        df_filtered = df_filtered[df_filtered["Rubro"].str.contains(normalize_str(rubro), na=False)]
    if establecimiento and establecimiento.lower() != "todos":
        df_filtered = df_filtered[df_filtered["Establecimiento"].str.contains(normalize_str(establecimiento), na=False)]
    if dia and dia.lower() != "todos":
        df_filtered = df_filtered[df_filtered["Día de la promoción"].str.contains(normalize_str(dia), na=False)]
    
    return df_filtered

@app.route("/")
def index():
    # Bancos, Rubros, Días
    bancos = sorted(df_promos["Banco/Billetera"].dropna().unique().tolist())
    rubros = ["Supermercado", "Cine", "Farmacia", "Combustible"]
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    return render_template("index.html", 
                           project_name="Simplificate",
                           bancos=bancos,
                           rubros=rubros,
                           dias=dias)

@app.route("/get_establecimientos", methods=["POST"])
def get_establecimientos():
    """Devuelve en JSON la lista de establecimientos para el rubro seleccionado."""
    rubro = request.form.get("rubro", "").strip().lower()
    df_temp = df_promos.copy()
    df_temp["Rubro"] = df_temp["Rubro"].apply(normalize_str)
    
    if rubro != "todos":
        df_temp = df_temp[df_temp["Rubro"].str.contains(rubro, na=False)]
    
    establecimientos = sorted(df_temp["Establecimiento"].dropna().unique().tolist())
    return jsonify({"establecimientos": establecimientos})

@app.route("/resultados", methods=["POST"])
def resultados():
    banco = request.form.get("banco_billetera")
    rubro = request.form.get("rubro")
    establecimiento = request.form.get("establecimiento")
    dia = request.form.get("dia")
    
    df_filtered = filter_promos(banco, rubro, establecimiento, dia)
    
    # Ajustamos columnas para agrupar
    group_cols = [
        "Banco/Billetera", "Rubro", "Establecimiento",
        "Descuento", "Tope de reintegro", "Se requiere", "Condiciones"
    ]
    
    # Reemplazar NaN en "Se requiere" por "n/a" para evitar "nan"
    df_filtered["Se requiere"] = df_filtered["Se requiere"].fillna("n/a").astype(str)
    df_filtered["Se requiere"] = df_filtered["Se requiere"].apply(
        lambda x: "n/a" if x.strip().lower() in ["nan", ""] else x
    )

    # Normalizar el resto de columnas
    for col in group_cols + ["Día de la promoción"]:
        df_filtered[col] = df_filtered[col].astype(str).str.strip()
    
    if not df_filtered.empty:
        df_grouped = df_filtered.groupby(group_cols, as_index=False)["Día de la promoción"].agg(
            lambda x: ", ".join(sorted(set(x)))
        )
    else:
        df_grouped = pd.DataFrame(columns=group_cols + ["Día de la promoción"])
    
    # Reemplazar "n/a" o vacíos en "Tope de reintegro" con "-"
    df_grouped["Tope de reintegro"] = df_grouped["Tope de reintegro"].apply(
        lambda x: x if pd.notnull(x) and str(x).strip().lower() != "n/a" else "-"
    )

    promociones = df_grouped.to_dict("records")
    return render_template("results.html", promociones=promociones, project_name="Simplificate")

if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=8000)