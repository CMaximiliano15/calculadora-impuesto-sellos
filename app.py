import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS

# ----------------------------------------------------------------------
# 1. INICIALIZACIÓN Y CARGA DE DATOS
# ----------------------------------------------------------------------

import numpy as np # Asegúrate de tener esta importación

app = Flask(__name__)
CORS(app)

try:
    # Carga tu archivo real
    df = pd.read_stata("G:\\Mi unidad\\Facultad (Eco)\\CEFIP\\Calculadora Sellos\\base_sellos_portal_v03.dta")

    # 1. Normalizar los nombres de columna a minúsculas
    df.columns = df.columns.str.lower()

    # 2. Limpieza de texto y conversión a NULOS reales
    for col in df.columns:
        if hasattr(df[col], 'str'):
            # Quitamos espacios y caracteres raros
            df[col] = df[col].str.replace('\xa0', ' ', regex=False).str.strip()
            
            # --- LA CLAVE ESTÁ AQUÍ ---
            # Reemplazamos el punto de Stata y los vacíos por NaN de Numpy
            df[col] = df[col].replace(['.', ''], np.nan)

    # 3. Conversión de 'year' a tipo entero
    df['year'] = pd.to_numeric(df['year'], errors='coerce').fillna(0).astype(int)

    if 'alicuota' not in df.columns:
        print("¡ADVERTENCIA! La columna 'alicuota' no fue encontrada.")

    # --- AUDITORÍA PARA VERIFICAR ---
    print("\n--- Conteo de SUBSUBACTIVIDAD (Sin Nulos) ---")
    # dropna=True (por defecto) hará que los 3149 y 464 ya no aparezcan en la lista
    print(df['subsubactividad'].value_counts())

except FileNotFoundError:
    print("¡ERROR! No se encontró el archivo .dta")
except Exception as e:
    print(f"Error en carga: {e}")


def auditar_base_de_datos(df):
    print("\n" + "="*40)
    print("RESUMEN DE DATOS CARGADOS")
    print("="*40)
    
    # Columnas que queremos revisar
    columnas_a_revisar = ['year', 'provincia', 'actividad', 'subactividad', 'subsubactividad']
    
    for col in columnas_a_revisar:
        if col in df.columns:
            print(f"\nConteo para la columna: '{col.upper()}'")
            # value_counts() cuenta cuántas veces aparece cada valor
            # sort_index() los ordena (por año o por nombre)
            print(df[col].value_counts().sort_index())
            print("-" * 20)
    
    print(f"\nTotal de filas cargadas: {len(df)}")
    print("="*40 + "\n")

# Llamamos a la función
auditar_base_de_datos(df)

# ----------------------------------------------------------------------
# 2. LÓGICA (Funciones de Filtrado)
# ----------------------------------------------------------------------

#Convierte los valores NaN a None para que JSON los maneje bien
#JSON (JavaScript Object Notation) es un formato estándar para enviar datos entre un servidor y un cliente web.
import numpy as np

def clean_json_nan(data):
    """Convierte np.nan/pd.isna() a None recursivamente para serialización JSON segura."""
    if isinstance(data, dict):
        return {k: clean_json_nan(v) for k, v in data.items()}
    if isinstance(data, list):
        return [clean_json_nan(v) for v in data]
    # Comprueba np.nan o pd.isna()
    if isinstance(data, float) and (np.isnan(data) or pd.isna(data)):
        return None
    return data


#Recibe el DataFrame, el nombre del filtro y los filtros previos aplicados
import pandas as pd
import numpy as np

#Recibe el DataFrame, el nombre del filtro y los filtros previos aplicados
# Función auxiliar para extraer opciones y eliminar el punto '.'

def get_clean_options(df_f, name):
    
    # 🛑 Validación CRÍTICA: La columna debe existir en el DataFrame filtrado.
    if name not in df_f.columns:
        return []
        
    # Si el DataFrame está vacío (aunque la columna exista), retornamos []
    if df_f.empty:
        return []
        
    # 1. Quitar NaN/None
    options_no_nan_raw = df_f[name].dropna().unique()
    
    # 2. Quitar el string '.'
    return [str(opcion) for opcion in options_no_nan_raw if str(opcion) != '.']

#Recibe el DataFrame, el nombre del filtro y los filtros previos aplicados
def get_filter_options(df: pd.DataFrame, filter_name: str, filters: dict = {}) -> list:
    print(f"--- Extrayendo opciones para '{filter_name}' con filtros previos: {filters} ---")
    df_filtered = df.copy()
    
    # ... (1. APLICACIÓN DE FILTROS PREVIOS - Sin cambios) ...
    # El bucle de filtros se aplica aquí
    for col, value in filters.items():
        if value is not None and value != '':
            value_cleaned = str(value).strip().replace('\xa0', ' ').replace('.0', '')
            
            if col == 'year':
                try:
                    target_value = int(value_cleaned)
                    df_filtered = df_filtered[(df_filtered[col] == target_value) & (df_filtered[col].notna())]
                except ValueError:
                    continue 
            else:
                df_filtered = df_filtered[
                    (df_filtered[col] == value_cleaned) & (df_filtered[col].notna())
                ]
    
    # 2. --- LÓGICA DE EXTRACCIÓN Y RESTRICCIÓN DINÁMICA ---
    options = []

    # 🛑 Si el DF está vacío aquí, devolvemos inmediatamente para evitar fallos.
    if df_filtered.empty:
        print(f"--- DataFrame filtrado está vacío para '{filter_name}'. Devolviendo []. ---")
        return []
        
    try:
        
        # --- A. LÓGICA ESPECÍFICA PARA sub_sub_actividad ---
        if filter_name == 'subsubctividad':
            
            # Ya que get_clean_options maneja el KeyError, solo comprobamos el caso de todos nulos
            if df_filtered[filter_name].isnull().all():
                options = [] 
            else:
                options = get_clean_options(df_filtered, filter_name)
        
        # --- B. LÓGICA ESPECÍFICA PARA subactividad ---
        elif filter_name == 'subactividad':
            
            options_no_dot = get_clean_options(df_filtered, filter_name)
            hay_nulos_originales = df_filtered[filter_name].isnull().any()
            
            if len(options_no_dot) == 0:
                options = ["N/A - Caso General"]
            else:
                options = options_no_dot
                if hay_nulos_originales:
                    options.append("N/A - Caso General")

        # --- C. MANEJO GENERAL (Provincia, Año, Actividad, etc.) ---
        else:
            options_no_dot = get_clean_options(df_filtered, filter_name)

            if len(options_no_dot) == 0:
                options = [] # Señal para el frontend de BLOCKEAR y SALTAR
            else:
                options = options_no_dot
                
    except Exception as e:
        # Esto captura errores si la columna realmente no existe, o fallos de tipo
        print(f"Error en extracción de opciones para '{filter_name}' (capturado): {e}")
        options = []

    # 3. --- FORMATO Y ORDEN (sin cambios) ---
    try:
        if 'options' in locals() and isinstance(options, list):
            options = [str(o).replace('.0', '') if str(o).endswith('.0') else str(o) for o in options]
            options.sort(key=lambda x: int(x) if x.isdigit() else x)
        else:
            options = []
    except Exception:
        options.sort()
    print(f"--- Opciones obtenidas para '{filter_name}': {options} ---")
    return options


def get_alicuota(df: pd.DataFrame, filters: dict) -> dict:
    print(f"--- Ejecutando búsqueda jerárquica con: {filters} ---")
    
    actividad = filters.get("actividad")
    subactividad = filters.get("subactividad")
    sub_sub = filters.get("subsubactividad")
    year = filters.get("year")
    provincia = filters.get("provincia")

    df_base = df.copy()
    if provincia:
        df_base = df_base[df_base["provincia"] == provincia] 
    if year:
        df_base = df_base[df_base["year"] == int(str(year).split('.')[0])]

    # ---- CASO CABA / PROVINCIAS SIN ACTIVIDAD ----
    if not actividad and subactividad:
        print(f"Buscando por subactividad directa (Caso CABA): {subactividad}")
        # Intentamos buscar el texto de la subactividad en ambas columnas por si acaso
        mask = (df_base["subactividad"] == subactividad) | (df_base["actividad"] == subactividad)
        df_caba = df_base[mask]
        if not df_caba.empty:
            return process_alicuota_result(df_caba)

    # ---- BÚSQUEDA JERÁRQUICA ESTÁNDAR ----
    # 1) Nivel 3
    if actividad and subactividad and sub_sub:
        res = df_base[(df_base["actividad"] == actividad) & 
                      (df_base["subactividad"] == subactividad) & 
                      (df_base["subsubactividad"] == sub_sub)]
        if not res.empty: return process_alicuota_result(res)

    # 2) Nivel 2
    if actividad and subactividad:
        res = df_base[(df_base["actividad"] == actividad) & 
                      (df_base["subactividad"] == subactividad)]
        if not res.empty: return process_alicuota_result(res)

    # 3) Nivel 1
    if actividad:
        res = df_base[df_base["actividad"] == actividad]
        if not res.empty: return process_alicuota_result(res)

    # 4) Fallback: Si hay una sola alícuota para toda la provincia/año
    if not df_base.empty and len(df_base['alicuota'].unique()) == 1:
        return process_alicuota_result(df_base)

    return {"status": "error", "message": "No se pudo obtener una alícuota específica."}


# --- MÓDULO SEPARADO: PROCESA EL RESULTADO DE ALICUOTA ---
def process_alicuota_result(df_filtered: pd.DataFrame) -> dict:
    # --- CASO DE MÚLTIPLES FILAS (TRAMOS/UMBRALES) ---
    if len(df_filtered) > 1:
        umbrales_list = []
        for _, r in df_filtered.iterrows():
            m_fijo = r.get('monto_fijo')
            detalle_fijo = ""
            
            # Lógica de Monto Fijo o Módulos por TRAMO
            if (pd.isna(m_fijo) or m_fijo == 0):
                m_mod = r.get('montomodulo')
                v_mod = r.get('valormodulo')
                if pd.notna(m_mod) and pd.notna(v_mod):
                    m_fijo = float(m_mod) * float(v_mod)
                    detalle_fijo = f"{m_mod} mod. x ${v_mod}"
            else:
                m_fijo = float(m_fijo)
                detalle_fijo = f"Monto fijo: ${m_fijo}"

            # Extraemos mínimos y máximos por tramo (si existen)
            m_min = r.get('monto_min')
            m_max = r.get('monto_max')

            umbrales_list.append({
                "desde": clean_json_nan(r.get('umbral_desde')),
                "hasta": clean_json_nan(r.get('umbral_hasta')),
                "alicuota_pct": round(float(r['alicuota']) * 100, 2) if pd.notna(r.get('alicuota')) else 0,
                "alicuota_fact": float(r['alicuota']) if pd.notna(r.get('alicuota')) else 0,
                "cargo_fijo_tramo": m_fijo if pd.notna(m_fijo) else 0,
                "detalle_fijo": detalle_fijo,
                "monto_min": float(m_min) if pd.notna(m_min) else 0,
                "monto_max": float(m_max) if pd.notna(m_max) else None 
            })

        return {
            "status": "varies",
            "message": "La alícuota depende de la Base Imponible.",
            "umbrales": clean_json_nan(umbrales_list)
        }

    # --- CASO DE FILA ÚNICA ---
    row = df_filtered.iloc[0]
    alicuota_raw = row.get('alicuota')
    monto_fijo_raw = row.get('monto_fijo')
    m_min = row.get('monto_min')
    m_max = row.get('monto_max')

    # 1. Caso de solo Monto Fijo (sin alícuota)
    if pd.isna(alicuota_raw) or alicuota_raw == 0:
        m_fijo_final = 0
        if pd.notna(monto_fijo_raw) and monto_fijo_raw != 0:
            m_fijo_final = float(monto_fijo_raw)
        elif pd.notna(row.get('montomodulo')) and pd.notna(row.get('valormodulo')):
            m_fijo_final = float(row['montomodulo']) * float(row['valormodulo'])
        
        return {
            "status": "fixed",
            "monto_fijo": m_fijo_final,
            "detalle": f"Monto fijo determinado: ${m_fijo_final}"
        }

    # 2. Caso de Alícuota Única (con posibles límites)
    # MODIFICACIÓN: Unificamos a 'alicuota_fact' para que el HTML reciba siempre el mismo nombre de variable
    resultado = {
        "status": "ok", 
        "alicuota_fact": float(alicuota_raw),
        "monto_min": float(m_min) if pd.notna(m_min) else 0,
        "monto_max": float(m_max) if pd.notna(m_max) else None 
    }
    
    # Cargo fijo adicional (si existe)
    if pd.notna(monto_fijo_raw) and monto_fijo_raw != 0:
        resultado["cargo_fijo_adicional"] = float(monto_fijo_raw)
    elif pd.notna(row.get('montomodulo')) and pd.notna(row.get('valormodulo')):
        resultado["cargo_fijo_adicional"] = float(row['montomodulo']) * float(row['valormodulo'])
    
    return resultado
# ----------------------------------------------------------------------
# 3. ENDPOINTS DE FLASK 
# ----------------------------------------------------------------------

@app.route('/api/options', methods=['POST'])
def get_options(): #Obtiene las opciones para un filtro dado
    try:
        print("--- Solicitud de opciones de filtro recibida ---: {}".format(request.get_json()))
        data = request.get_json() #Recibe el JSON del frontend
        filter_name = data.get('filter_name') #Nombre del filtro a obtener
        previous_filters = data.get('filters', {}) #Filtros previos aplicados

        if not filter_name:
            return jsonify({"error": "Falta 'filter_name'."}), 400

        options = get_filter_options(df, filter_name, previous_filters)
        print(f"(get_options)--- Enviando opciones para '{filter_name}': {options} ---")
        return jsonify({"options": options})

    except Exception as e:
        print(f"Error al obtener opciones: {e}")
        return jsonify({"error": "Eror interno del servidor."}), 500

@app.route('/api/alicuota', methods=['POST'])
def calculate_alicuota():
    try:
        final_filters = request.get_json()
        print(f"--- POST /api/alicuota: {final_filters} ---")
        
        # Solo provincia y año son estrictamente obligatorios para el servidor
        if not final_filters.get('provincia') or not final_filters.get('year'):
            return jsonify({"result": {"status": "error", "message": "Provincia y Año son requeridos."}})

        # Ejecutar lógica de búsqueda
        result = get_alicuota(df, final_filters)
        
        # IMPORTANTE: Siempre devolvemos bajo la llave 'result' para el frontend
        return jsonify({"result": result})

    except Exception as e:
        print(f"Error crítico en calculate_alicuota: {e}")
        return jsonify({"result": {"status": "error", "message": str(e)}})


if __name__ == '__main__':
    print("\n--- Servidor Flask Iniciado ---")
    app.run(debug=True)