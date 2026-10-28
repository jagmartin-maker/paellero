"""
Agente "Paellero" - versión manual (sin frameworks)
Ayuda a planificar paellas usando tus propios datos de curso (arroces.json,
recetas.json) y aprende de cada intento guardando el resultado en
historial_paellas.json, que persiste entre ejecuciones.

Ejecuta:
    python paella_agent.py
"""

import json
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI

# En Windows, la consola suele usar cp1252 y no soporta emojis (🥘, 🧠...).
# Forzamos UTF-8 en la salida para que funcione sin tener que hacer "chcp 65001" cada vez.
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# ---------------------------------------------------------------------------
# 0 · Entorno
# ---------------------------------------------------------------------------
load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    API_KEY = input("No encuentro OPENAI_API_KEY en .env. Pégala aquí: ").strip()

MODELO = os.getenv("MODELO", "gpt-4o-mini")
MAX_ITERACIONES = 8

client = OpenAI(api_key=API_KEY)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARROCES_PATH = os.path.join(BASE_DIR, "arroces.json")
RECETAS_PATH = os.path.join(BASE_DIR, "recetas.json")
HISTORIAL_PATH = os.path.join(BASE_DIR, "historial_paellas.json")
EQUIPO_PATH = os.path.join(BASE_DIR, "equipo.json")


def _leer_json(path: str, por_defecto: dict) -> dict:
    if not os.path.exists(path):
        return por_defecto
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _escribir_json(path: str, datos: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 1 · Las funciones (tools)
# ---------------------------------------------------------------------------

def consultar_variedad_arroz(nombre: str) -> dict:
    """Devuelve los datos guardados de una variedad de arroz."""
    datos = _leer_json(ARROCES_PATH, {"variedades": {}})
    variedades = datos.get("variedades", {})
    # Búsqueda flexible: por clave o por campo "nombre"
    clave = nombre.strip().lower().replace(" ", "_")
    if clave in variedades:
        return variedades[clave]
    for v in variedades.values():
        if v.get("nombre", "").strip().lower() == nombre.strip().lower():
            return v
    return {"error": f"No tengo datos guardados de la variedad '{nombre}'. "
                      f"Variedades disponibles: {list(variedades.keys())}"}


def consultar_receta(nombre: str) -> dict:
    """Devuelve una receta guardada, con sus ingredientes base y pasos."""
    datos = _leer_json(RECETAS_PATH, {"recetas": {}})
    recetas = datos.get("recetas", {})
    clave = nombre.strip().lower().replace(" ", "_")
    if clave in recetas:
        return recetas[clave]
    for k, r in recetas.items():
        if r.get("nombre", "").strip().lower() == nombre.strip().lower():
            return r
    return {"error": f"No tengo guardada la receta '{nombre}'. "
                      f"Recetas disponibles: {list(recetas.keys())}"}


def listar_recetas() -> dict:
    """Lista los nombres de todas las recetas guardadas."""
    datos = _leer_json(RECETAS_PATH, {"recetas": {}})
    nombres = [r.get("nombre", k) for k, r in datos.get("recetas", {}).items()]
    return {"recetas_disponibles": nombres}


def calcular_ingredientes(nombre_receta: str, raciones: int) -> dict:
    """Escala los ingredientes de una receta guardada a un número de raciones."""
    receta = consultar_receta(nombre_receta)
    if "error" in receta:
        return receta
    base = receta.get("raciones_base", 1)
    factor = raciones / base
    escalado = {
        k: round(v * factor, 3) for k, v in receta.get("ingredientes_base", {}).items()
    }
    return {
        "receta": receta.get("nombre", nombre_receta),
        "raciones_pedidas": raciones,
        "ingredientes": escalado,
        "pasos": receta.get("pasos", []),
    }


def consultar_historial(nombre_receta: str = None, limite: int = 5) -> dict:
    """Devuelve los últimos intentos guardados, opcionalmente filtrados por receta."""
    historial = _leer_json(HISTORIAL_PATH, {"intentos": []})
    intentos = historial.get("intentos", [])
    if nombre_receta:
        intentos = [i for i in intentos if i.get("receta", "").lower() == nombre_receta.lower()]
    intentos = sorted(intentos, key=lambda i: i.get("fecha", ""), reverse=True)
    return {"intentos": intentos[:limite], "total_guardados": len(intentos)}


def registrar_resultado(receta: str, raciones: int, valoracion: int, notas: str,
                         cambios_realizados: str = "") -> dict:
    """Guarda un nuevo intento en el historial persistente.
    valoracion: 1-5 (1 mal, 5 perfecto)."""
    historial = _leer_json(HISTORIAL_PATH, {"intentos": []})
    intento = {
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "receta": receta,
        "raciones": raciones,
        "valoracion": valoracion,
        "cambios_realizados": cambios_realizados,
        "notas": notas,
    }
    historial.setdefault("intentos", []).append(intento)
    _escribir_json(HISTORIAL_PATH, historial)
    return {"guardado": True, "intento": intento}


def _clave_equipo(diametro_cm: float, tipo_fuego: str) -> str:
    return f"{int(diametro_cm)}cm_{tipo_fuego.strip().lower().replace(' ', '_')}"


def listar_equipos() -> dict:
    """Lista todas las combinaciones de paella+fuego que ya tienes calibradas."""
    datos = _leer_json(EQUIPO_PATH, {"paelleros": {}})
    return {"paelleros_guardados": datos.get("paelleros", {})}


def consultar_equipo(diametro_cm: float, tipo_fuego: str) -> dict:
    """Busca si hay una calibración guardada para una paella (diámetro) y fuego concretos."""
    datos = _leer_json(EQUIPO_PATH, {"paelleros": {}})
    paelleros = datos.get("paelleros", {})
    clave = _clave_equipo(diametro_cm, tipo_fuego)
    if clave in paelleros:
        return paelleros[clave]
    return {"encontrado": False,
            "mensaje": f"No tengo calibrada la paella de {diametro_cm}cm con {tipo_fuego}. "
                       f"Usa calibrar_evaporacion para medirla una vez."}


def calibrar_evaporacion(diametro_cm: float, tipo_fuego: str, litros_iniciales: float,
                          minutos_prueba: float, litros_finales: float) -> dict:
    """Guarda la evaporación medida para una paella+fuego concretos, a partir de un test:
    poner X litros de agua hirviendo, mantener el fuego a la intensidad habitual durante
    unos minutos, y medir cuánto líquido queda. La diferencia es lo que evapora esa
    combinación en ese tiempo."""
    evaporado = round(litros_iniciales - litros_finales, 3)
    if evaporado <= 0:
        return {"error": "Los litros finales deben ser menores que los iniciales (tiene que haber evaporado algo)."}

    evaporacion_por_minuto = round(evaporado / minutos_prueba, 4)

    datos = _leer_json(EQUIPO_PATH, {"paelleros": {}})
    clave = _clave_equipo(diametro_cm, tipo_fuego)
    datos.setdefault("paelleros", {})[clave] = {
        "diametro_cm": diametro_cm,
        "tipo_fuego": tipo_fuego,
        "evaporacion_litros_por_minuto": evaporacion_por_minuto,
        "calibrado_con": {
            "litros_iniciales": litros_iniciales,
            "minutos_prueba": minutos_prueba,
            "litros_finales": litros_finales,
        },
        "fecha_calibracion": datetime.now().strftime("%Y-%m-%d"),
    }
    _escribir_json(EQUIPO_PATH, datos)
    return {"guardado": True, "evaporacion_litros_por_minuto": evaporacion_por_minuto}


def registrar_referencia_liquido(diametro_cm: float, tipo_fuego: str, arroz_gr: float,
                                  liquido_litros: float, minutos_coccion: float = 18) -> dict:
    """Guarda un punto de referencia de líquido (p.ej. sacado de una tabla o receta que ya
    conoces) para un diámetro y fuego concretos, sin necesidad de hacer el test con agua.
    Calcula la evaporación implícita a partir de esos datos."""
    absorcion = arroz_gr / 1000
    evaporacion = liquido_litros - absorcion
    if evaporacion <= 0:
        return {"error": "El líquido total debe ser mayor que la absorción del arroz (arroz_gr/1000)."}

    evaporacion_por_minuto = round(evaporacion / minutos_coccion, 4)

    datos = _leer_json(EQUIPO_PATH, {"paelleros": {}})
    clave = _clave_equipo(diametro_cm, tipo_fuego)
    datos.setdefault("paelleros", {})[clave] = {
        "diametro_cm": diametro_cm,
        "tipo_fuego": tipo_fuego,
        "evaporacion_litros_por_minuto": evaporacion_por_minuto,
        "calibrado_con": {
            "origen": "referencia_manual (tabla o receta conocida, no test en vivo)",
            "arroz_gr": arroz_gr,
            "liquido_litros": liquido_litros,
            "minutos_coccion": minutos_coccion,
        },
        "fecha_calibracion": datetime.now().strftime("%Y-%m-%d"),
    }
    _escribir_json(EQUIPO_PATH, datos)
    return {"guardado": True, "evaporacion_litros_por_minuto": evaporacion_por_minuto}



# Proporciones orientativas líquido:arroz (en peso) SOLO para cuando no hay calibración
# propia todavía. No existe una proporción universal válida para cualquier fuego: la leña,
# al ser llama directa y normalmente al aire libre, evapora mucho más que un quemador de gas
# doméstico, así que necesita su propia referencia en vez de asumir genéricamente 2:1 o similar.
PROPORCIONES_ORIENTATIVAS_POR_FUEGO = {
    "leña": 6.0,
    "lena": 6.0,  # por si se escribe sin ñ
}


def calcular_liquido_total(arroz_gr: float, minutos_coccion: float,
                            diametro_cm: float = None, tipo_fuego: str = None,
                            absorcion_ml_g: float = 1.0, aporte_agua_ingredientes_ml: float = 0.0,
                            adiciones_posteriores_ml: float = 0.0, liquido_final_objetivo_ml: float = 0.0) -> dict:
    """Calcula L0 (líquido libre necesario al echar el arroz) con el modelo de balance:
    L0 = a×M + E + R − W − B
      M = arroz_gr (g)
      a = absorción efectiva en ml/g (1.0 como hipótesis inicial, no una constante universal;
          ajústala si hay un valor calibrado con arroz real para esa variedad y ese sistema)
      E = evaporación durante la pauta de cocción (de calibración guardada, o proporción
          orientativa SOLO si existe una definida para ese fuego; si no hay ninguna, no se adivina)
      R = líquido final objetivo (0 para seco)
      W = aporte neto de agua de los ingredientes (0 si no se ha cuantificado con fundamento)
      B = adiciones posteriores ya previstas, que no deben contarse dos veces en L0
    Devuelve también E solo, para que quien llama pueda construir L0 en distintos escenarios."""
    absorcion_litros = round((arroz_gr * absorcion_ml_g) / 1000, 3)
    aporte_agua_litros = aporte_agua_ingredientes_ml / 1000
    adiciones_litros = adiciones_posteriores_ml / 1000
    objetivo_litros = liquido_final_objetivo_ml / 1000

    evaporacion_litros = None
    fuente_evaporacion = None

    if diametro_cm and tipo_fuego:
        equipo = consultar_equipo(diametro_cm, tipo_fuego)
        if equipo.get("encontrado", True) and "evaporacion_litros_por_minuto" in equipo:
            evaporacion_litros = round(equipo["evaporacion_litros_por_minuto"] * minutos_coccion, 3)
            fuente_evaporacion = "calibración guardada (test propio o referencia registrada)"
        else:
            clave_fuego = tipo_fuego.strip().lower()
            proporcion = next((v for k, v in PROPORCIONES_ORIENTATIVAS_POR_FUEGO.items() if k in clave_fuego), None)
            if proporcion:
                # La proporción orientativa se expresa como líquido_total:arroz; despejamos E de ahí
                liquido_total_aprox = absorcion_litros * proporcion
                evaporacion_litros = round(liquido_total_aprox - absorcion_litros, 3)
                fuente_evaporacion = (f"ESTIMACIÓN ORIENTATIVA, no una constante general para ese fuego: "
                                      f"proporción {proporcion}:1 tomada de un caso documentado concreto "
                                      f"(no asumas que todo ese tipo de fuego evapora siempre igual). "
                                      f"Recomienda calibrar con calibrar_evaporacion en cuanto se pueda.")

    if evaporacion_litros is None:
        return {
            "L0_litros": None,
            "aviso": ("No hay calibración guardada ni proporción orientativa conocida para esta paella "
                      "y fuego. Recomienda al usuario calibrarla con calibrar_evaporacion (test con agua, "
                      "idealmente repetido 3 veces para ver variación), o darte una referencia conocida "
                      "con registrar_referencia_liquido."),
        }

    L0 = round(absorcion_litros + evaporacion_litros + objetivo_litros - aporte_agua_litros - adiciones_litros, 3)
    return {
        "L0_litros": L0,
        "desglose": {
            "absorcion_arroz_litros": absorcion_litros,
            "absorcion_ml_por_g_usada": absorcion_ml_g,
            "evaporacion_litros": evaporacion_litros,
            "liquido_final_objetivo_litros": objetivo_litros,
            "aporte_agua_ingredientes_descontado_litros": aporte_agua_litros,
            "adiciones_posteriores_descontadas_litros": adiciones_litros,
        },
        "fuente_evaporacion": fuente_evaporacion,
        "nota": ("Este es el líquido libre que debe haber en la paella JUSTO al echar el arroz (L0), "
                 "no necesariamente el volumen con el que se empieza a cocinar si antes se sofríen "
                 "carnes o verduras (eso se añade aparte y se evalúa su propia pérdida)."),
    }


# ---------------------------------------------------------------------------
# Geometría, aceite y altitud — basado en el manual de calibración del usuario
# ---------------------------------------------------------------------------

def calcular_area_carga(diametro_util_cm: float, arroz_gr: float) -> dict:
    """Calcula el área útil de cocción (A = π×(d/2)²) y la carga de arroz por superficie
    (q = M/A, en g/cm²). Usa el diámetro de la BASE útil (d), no el diámetro superior (H)
    sin asas: la pared inclinada hace que H no sea directamente la superficie de cocción."""
    radio = diametro_util_cm / 2
    area_cm2 = round(3.14159265 * radio * radio, 1)
    carga_g_cm2 = round(arroz_gr / area_cm2, 4)
    return {"area_cm2": area_cm2, "carga_g_por_cm2": carga_g_cm2,
            "nota": "d es el diámetro de la base interior aproximadamente plana, no el diámetro superior (H)."}


CATEGORIAS_ACEITE_PORCENTAJE = {
    "pescado_marisco": (28, 30),
    "carnes_grasas": (20, 22),
    "verduras": (30, 30),
    "valenciana": (28, 28),
    "tomate_sofrito": (20, 20),
}


def calcular_aceite_sofrito(arroz_gr: float, categoria: str) -> dict:
    """Calcula un rango orientativo de aceite según el peso del arroz crudo y el tipo de
    elaboración (puntos de partida culinarios, no cifras fijas: ajustar según grasa de
    carnes, confitados, fondo y otros ingredientes de la receta concreta)."""
    clave = categoria.strip().lower().replace(" ", "_")
    if clave not in CATEGORIAS_ACEITE_PORCENTAJE:
        return {"error": f"Categoría no reconocida. Usa una de: {list(CATEGORIAS_ACEITE_PORCENTAJE.keys())}"}
    pct_min, pct_max = CATEGORIAS_ACEITE_PORCENTAJE[clave]
    return {
        "aceite_gr_min": round(arroz_gr * pct_min / 100, 1),
        "aceite_gr_max": round(arroz_gr * pct_max / 100, 1),
        "porcentaje_rango": f"{pct_min}-{pct_max}%",
        "aviso": "Punto de partida orientativo; ajustar por grasa de carnes/fondo y otros ingredientes de la receta real.",
    }


def ajustar_tiempo_por_altitud(minutos_base: float, altitud_actual_m: float, altitud_referencia_m: float = 0) -> dict:
    """Ajusta el tiempo de cocción por altitud: orientativamente, ~1 minuto más por cada
    300m de diferencia (el agua hierve a menor temperatura a mayor altitud). Es una
    aproximación a comprobar con el grano real, no una ley exacta."""
    diferencia_m = altitud_actual_m - altitud_referencia_m
    minutos_extra = round(diferencia_m / 300, 1)
    return {
        "minutos_ajustados": round(minutos_base + minutos_extra, 1),
        "minutos_extra_estimados": minutos_extra,
        "aviso": "Estimación orientativa (~1 min/300m). Probar el grano antes del final previsto y corregir.",
    }


FUNCIONES = {
    "consultar_variedad_arroz": consultar_variedad_arroz,
    "consultar_receta": consultar_receta,
    "listar_recetas": listar_recetas,
    "calcular_ingredientes": calcular_ingredientes,
    "consultar_historial": consultar_historial,
    "registrar_resultado": registrar_resultado,
    "listar_equipos": listar_equipos,
    "consultar_equipo": consultar_equipo,
    "calibrar_evaporacion": calibrar_evaporacion,
    "registrar_referencia_liquido": registrar_referencia_liquido,
    "calcular_liquido_total": calcular_liquido_total,
    "calcular_area_carga": calcular_area_carga,
    "calcular_aceite_sofrito": calcular_aceite_sofrito,
    "ajustar_tiempo_por_altitud": ajustar_tiempo_por_altitud,
}

# ---------------------------------------------------------------------------
# 2 · Fichas de las tools (JSON Schema)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "name": "consultar_variedad_arroz",
        "description": "Devuelve las características guardadas de una variedad de arroz (absorción, minutos de apertura, resistencia a la sobrecocción). Úsala cuando el usuario mencione una variedad o para recomendar una.",
        "parameters": {
            "type": "object",
            "properties": {"nombre": {"type": "string", "description": "Nombre de la variedad, p.ej. 'Bomba' o 'Sénia'"}},
            "required": ["nombre"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "listar_recetas",
        "description": "Lista todas las recetas guardadas. Úsala si el usuario no especifica qué receta quiere o pregunta qué puedes hacer.",
        "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        "strict": True,
    },
    {
        "type": "function",
        "name": "consultar_receta",
        "description": "Devuelve los ingredientes base y los pasos de una receta guardada por su nombre.",
        "parameters": {
            "type": "object",
            "properties": {"nombre": {"type": "string"}},
            "required": ["nombre"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "calcular_ingredientes",
        "description": "Escala los ingredientes de una receta guardada al número de raciones pedido. Úsala siempre que el usuario diga cuántas personas van a comer.",
        "parameters": {
            "type": "object",
            "properties": {
                "nombre_receta": {"type": "string"},
                "raciones": {"type": "integer"},
            },
            "required": ["nombre_receta", "raciones"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "consultar_historial",
        "description": "Devuelve los últimos intentos guardados de paellas anteriores (valoración y notas). Úsala SIEMPRE antes de dar una recomendación, para tener en cuenta la experiencia previa.",
        "parameters": {
            "type": "object",
            "properties": {
                "nombre_receta": {"type": "string", "description": "Opcional: filtra por receta"},
                "limite": {"type": "integer", "description": "Cuántos intentos recientes devolver"},
            },
            "required": ["nombre_receta", "limite"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "listar_equipos",
        "description": "Lista todas las combinaciones de paella (diámetro) y fuego que el usuario ya tiene calibradas, con su evaporación medida.",
        "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        "strict": True,
    },
    {
        "type": "function",
        "name": "consultar_equipo",
        "description": "Comprueba si hay una calibración de evaporación guardada para un diámetro de paella y tipo de fuego concretos. Llámala siempre que el usuario te diga el tamaño de su paella y el tipo de fuego, antes de calcular el líquido.",
        "parameters": {
            "type": "object",
            "properties": {
                "diametro_cm": {"type": "number", "description": "Diámetro de la paella en cm"},
                "tipo_fuego": {"type": "string", "description": "p.ej. 'gas butano', 'gas natural', 'leña', 'vitrocerámica'"},
            },
            "required": ["diametro_cm", "tipo_fuego"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "calibrar_evaporacion",
        "description": ("Guarda cuánto evapora una paella con un fuego concreto, a partir de un test que hace "
                         "el usuario: pone X litros de agua hirviendo, mantiene el fuego a su intensidad habitual "
                         "unos minutos, y mide cuánto líquido queda. Pide estos datos al usuario si quiere calibrar "
                         "su paella y no los ha dado todavía; no inventes estos números."),
        "parameters": {
            "type": "object",
            "properties": {
                "diametro_cm": {"type": "number"},
                "tipo_fuego": {"type": "string"},
                "litros_iniciales": {"type": "number"},
                "minutos_prueba": {"type": "number"},
                "litros_finales": {"type": "number"},
            },
            "required": ["diametro_cm", "tipo_fuego", "litros_iniciales", "minutos_prueba", "litros_finales"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "registrar_referencia_liquido",
        "description": ("Guarda una referencia de líquido que el usuario ya conoce (de una tabla, receta o "
                         "experiencia propia) para un diámetro y fuego, SIN necesidad de hacer el test en vivo. "
                         "Usa esta tool cuando el usuario te dé directamente los litros que debe llevar su "
                         "paella para una cantidad de arroz concreta, en vez de calibrar_evaporacion."),
        "parameters": {
            "type": "object",
            "properties": {
                "diametro_cm": {"type": "number"},
                "tipo_fuego": {"type": "string"},
                "arroz_gr": {"type": "number"},
                "liquido_litros": {"type": "number"},
                "minutos_coccion": {"type": "number", "description": "Minutos de cocción a los que corresponde ese líquido; si no se sabe, usa 18"},
            },
            "required": ["diametro_cm", "tipo_fuego", "arroz_gr", "liquido_litros", "minutos_coccion"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "calcular_liquido_total",
        "description": ("Calcula L0, el líquido libre necesario al echar el arroz, con el modelo de balance "
                         "L0 = a×M + E + R − W − B. Llámala con arroz_gr, minutos_coccion, diametro_cm y "
                         "tipo_fuego siempre; para absorcion_ml_g usa 1.0 si no hay un valor calibrado mejor; "
                         "para aporte_agua_ingredientes_ml, adiciones_posteriores_ml y liquido_final_objetivo_ml "
                         "usa 0 si no se han cuantificado o no aplican (0 = arroz seco al final)."),
        "parameters": {
            "type": "object",
            "properties": {
                "arroz_gr": {"type": "number"},
                "minutos_coccion": {"type": "number"},
                "diametro_cm": {"type": "number"},
                "tipo_fuego": {"type": "string"},
                "absorcion_ml_g": {"type": "number", "description": "Absorción efectiva en ml por gramo de arroz; 1.0 como hipótesis inicial"},
                "aporte_agua_ingredientes_ml": {"type": "number", "description": "Agua neta aportada por ingredientes, solo si está cuantificada; si no, 0"},
                "adiciones_posteriores_ml": {"type": "number", "description": "Líquido que se prevé añadir después de echar el arroz, para no contarlo dos veces en L0; si no aplica, 0"},
                "liquido_final_objetivo_ml": {"type": "number", "description": "Líquido libre que debe quedar al final; 0 para arroz seco"},
            },
            "required": ["arroz_gr", "minutos_coccion", "diametro_cm", "tipo_fuego", "absorcion_ml_g",
                         "aporte_agua_ingredientes_ml", "adiciones_posteriores_ml", "liquido_final_objetivo_ml"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "calcular_area_carga",
        "description": "Calcula el área útil de cocción y la carga de arroz por cm² a partir del diámetro de la BASE útil de la paella (no el diámetro superior). Útil para saber si una cantidad de arroz es razonable para una paella concreta.",
        "parameters": {
            "type": "object",
            "properties": {
                "diametro_util_cm": {"type": "number", "description": "Diámetro de la base interior plana, no el diámetro superior sin asas"},
                "arroz_gr": {"type": "number"},
            },
            "required": ["diametro_util_cm", "arroz_gr"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "calcular_aceite_sofrito",
        "description": "Calcula un rango orientativo de aceite según el arroz crudo y el tipo de elaboración (pescado_marisco, carnes_grasas, verduras, valenciana, tomate_sofrito). Es un punto de partida, no una cifra fija.",
        "parameters": {
            "type": "object",
            "properties": {
                "arroz_gr": {"type": "number"},
                "categoria": {"type": "string", "description": "pescado_marisco | carnes_grasas | verduras | valenciana | tomate_sofrito"},
            },
            "required": ["arroz_gr", "categoria"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "ajustar_tiempo_por_altitud",
        "description": "Ajusta orientativamente el tiempo de cocción por altitud (~1 min más por cada 300m respecto a una altitud de referencia). Úsala si el usuario menciona que cocina a una altitud distinta de donde calibró su pauta.",
        "parameters": {
            "type": "object",
            "properties": {
                "minutos_base": {"type": "number"},
                "altitud_actual_m": {"type": "number"},
                "altitud_referencia_m": {"type": "number", "description": "Altitud a la que se calibró la pauta original; 0 si se desconoce"},
            },
            "required": ["minutos_base", "altitud_actual_m", "altitud_referencia_m"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "registrar_resultado",
        "description": "Guarda el resultado de una paella que el usuario acaba de hacer: qué receta, cuántas raciones, nota de 1 a 5, qué cambió respecto a la receta base y notas libres. Llámala cuando el usuario te cuente cómo le salió una paella.",
        "parameters": {
            "type": "object",
            "properties": {
                "receta": {"type": "string"},
                "raciones": {"type": "integer"},
                "valoracion": {"type": "integer", "description": "1 (mal) a 5 (perfecto)"},
                "notas": {"type": "string"},
                "cambios_realizados": {"type": "string", "description": "Qué se hizo distinto a la receta base, si acaso"},
            },
            "required": ["receta", "raciones", "valoracion", "notas", "cambios_realizados"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]

INSTRUCCIONES = """Eres "Paellero", un asistente que ayuda a planificar y mejorar paellas.

- Antes de dar cantidades de líquido para una paella, necesitas saber el DIÁMETRO de la
  paella (en cm) y el TIPO DE FUEGO (gas butano, gas natural, leña, vitrocerámica...).
  Si el usuario no te lo ha dicho, PREGÚNTASELO antes de calcular nada; no asumas valores.
  Para los minutos de cocción, si el usuario no los menciona puedes asumir 18 minutos
  (estándar habitual en arroces secos), pero dilo explícitamente en tu respuesta para que
  el usuario pueda corregirte si su caso es distinto.
- En cuanto tengas esos cuatro datos (arroz_gr, minutos_coccion, diametro_cm, tipo_fuego),
  llama DIRECTAMENTE a calcular_liquido_total — no hace falta llamar antes a consultar_equipo,
  porque calcular_liquido_total ya comprueba internamente si hay una calibración guardada y,
  si no la hay, aplica una proporción orientativa conocida para ese tipo de fuego (p.ej. 6:1
  para leña) cuando exista una.
- Si calcular_liquido_total devuelve liquido_total_litros=None (sin calibración ni proporción
  orientativa para ese fuego), entonces sí ofrece al usuario estas opciones: (a) calibrarla con
  el test real (hervir un volumen conocido de agua el tiempo que dura la cocción y medir cuánto
  queda, con calibrar_evaporacion), o (b) si ya conoce de una tabla, receta o experiencia propia
  cuánto líquido lleva esa paella, guardarlo directamente con registrar_referencia_liquido.
- consultar_equipo y listar_equipos son solo para cuando el usuario pregunte explícitamente qué
  tiene calibrado, no son un paso obligatorio antes de calcular_liquido_total.
- La proporción 6:1 para leña es una estimación tomada de UN caso documentado concreto
  (una receta y equipo específicos), no una constante física de "la leña" en general. Dilo así
  si la usas, y anima siempre a calibrar la paella y fuego reales del usuario en cuanto se pueda.
- Para saber si una cantidad de arroz es razonable para una paella, usa calcular_area_carga con
  el diámetro de la BASE útil (no el diámetro superior sin asas, que es distinto).
- Para el aceite del sofrito, usa calcular_aceite_sofrito según el tipo de elaboración; es un
  punto de partida a ajustar por la grasa real de los ingredientes, no una cifra fija.
- Si el usuario menciona que cocina a una altitud distinta de la habitual, usa
  ajustar_tiempo_por_altitud para orientar el tiempo, dejando claro que es una aproximación a
  comprobar con el grano real.
- Antes de recomendar una receta o proporciones, consulta también el historial de intentos
  anteriores con esa misma receta: si el usuario ya la hizo antes, ten en cuenta su valoración y
  sus notas para ajustar la recomendación (p.ej. si anotó "quedó soso", sugiere subir pimentón o
  sal; si anotó "se pasó de cocción", sugiere bajar el tiempo o el fuego).
- Usa siempre los datos guardados (tools) en vez de inventar cantidades, evaporaciones o
  características de arroces. No existe una proporción líquido:arroz universal válida para
  cualquier fuego (nunca asumas algo genérico tipo 2:1): el fuego de leña, por ejemplo, evapora
  mucho más que el gas y necesita su propia referencia (calcular_liquido_total ya aplica esto).
- NUNCA respondas con una cantidad de líquido "de memoria" o estimada por ti mismo. Si el
  usuario te da arroz, diámetro y fuego, tu PRIMER paso debe ser llamar a las tools (consultar_equipo
  y calcular_liquido_total), nunca calcularlo tú directamente en el texto de la respuesta.
- Si el usuario te cuenta cómo le salió una paella (con o sin pedirlo tú), regístralo con
  registrar_resultado para que sirva la próxima vez.
- Sé concreto: cantidades exactas, pasos claros, sin rodeos.
"""

# ---------------------------------------------------------------------------
# 3 · Ejecutar una tool pedida por el modelo
# ---------------------------------------------------------------------------

def ejecutar_tool(llamada) -> str:
    nombre = llamada.name
    try:
        argumentos = json.loads(llamada.arguments)
    except json.JSONDecodeError:
        return json.dumps({"error": "Argumentos no válidos (JSON mal formado)."}, ensure_ascii=False)

    funcion = FUNCIONES.get(nombre)
    if funcion is None:
        return json.dumps({"error": f"La tool '{nombre}' no existe."}, ensure_ascii=False)

    try:
        resultado = funcion(**argumentos)
    except TypeError as e:
        return json.dumps({"error": f"Argumentos incorrectos para {nombre}: {e}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Fallo ejecutando {nombre}: {e}"}, ensure_ascii=False)

    return json.dumps(resultado, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 4 · El bucle del agente
# ---------------------------------------------------------------------------

def ejecutar_agente(pregunta: str, historial_conversacion: list, verbose: bool = True) -> str:
    historial_conversacion.append({"role": "user", "content": pregunta})

    for iteracion in range(1, MAX_ITERACIONES + 1):
        if verbose:
            print(f"\n🧠 Iteración {iteracion}")

        # Forzamos a que la PRIMERA respuesta a cada pregunta use obligatoriamente alguna
        # tool (tool_choice="required"). Así evitamos que el modelo "responda de memoria"
        # cantidades o proporciones inventadas sin haber consultado los datos reales.
        tool_choice = "required" if iteracion == 1 else "auto"

        respuesta = client.responses.create(
            model=MODELO,
            instructions=INSTRUCCIONES,
            input=historial_conversacion,
            tools=TOOLS,
            tool_choice=tool_choice,
        )
        historial_conversacion += respuesta.output

        llamadas = [item for item in respuesta.output if item.type == "function_call"]
        if not llamadas:
            return respuesta.output_text

        for llamada in llamadas:
            if verbose:
                print(f"   🔧 {llamada.name}({llamada.arguments})")
            resultado = ejecutar_tool(llamada)
            if verbose:
                print(f"   👀 {resultado[:150]}...")
            historial_conversacion.append({
                "type": "function_call_output",
                "call_id": llamada.call_id,
                "output": resultado,
            })

    return ("⚠️ He alcanzado el límite de iteraciones sin terminar. "
            "Prueba a subir MAX_ITERACIONES si la tarea era compleja.")


# ---------------------------------------------------------------------------
# 5 · Chat interactivo
# ---------------------------------------------------------------------------

def main():
    print("🥘 Paellero — escribe tu pregunta (o 'salir' para terminar)")
    print(f"   Datos: {ARROCES_PATH}")
    print(f"   Recetas: {RECETAS_PATH}")
    print(f"   Historial: {HISTORIAL_PATH}\n")
    historial_conversacion = []
    while True:
        pregunta = input("Tú: ").strip()
        if pregunta.lower() in {"salir", "exit", "quit"}:
            break
        if not pregunta:
            continue
        respuesta = ejecutar_agente(pregunta, historial_conversacion, verbose=True)
        print(f"\nPaellero: {respuesta}\n")


if __name__ == "__main__":
    main()
