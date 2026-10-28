"""
Paellero - interfaz web (Streamlit) para compartir el agente por internet.

Reutiliza TODA la lógica de datos y del bucle del agente de paella_agent.py
(recetas, arroces, equipo, historial) - esto es solo la capa de interfaz.

Ejecutar en local:
    streamlit run app.py

Desplegar gratis en internet: ver README.md, sección "Compartir por internet".
"""

import os

import streamlit as st

# IMPORTANTE: inyectamos la API key desde los "secrets" de Streamlit ANTES de
# importar paella_agent, para que el módulo la encuentre en el entorno y no
# intente pedirla de forma interactiva con input() (eso colgaría la app web).
if "OPENAI_API_KEY" in st.secrets:
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
if "MODELO" in st.secrets:
    os.environ["MODELO"] = st.secrets["MODELO"]

import paella_agent as base  # noqa: E402 (import tras configurar el entorno a propósito)

st.set_page_config(page_title="Paellero", page_icon="🥘")
st.title("🥘 Paellero")
st.caption("Tu asistente de paellas: recetas, cantidades y memoria de cada intento.")

if not os.getenv("OPENAI_API_KEY"):
    st.error(
        "Falta configurar OPENAI_API_KEY en los 'Secrets' de la app "
        "(Settings → Secrets en Streamlit Community Cloud, o .streamlit/secrets.toml en local)."
    )
    st.stop()

# --- Estado de la sesión ---------------------------------------------------
# api_historial: lo que se le pasa a ejecutar_agente (formato de la API de OpenAI)
# chat_display: solo para pintar los globos de chat en pantalla
if "api_historial" not in st.session_state:
    st.session_state.api_historial = []
if "chat_display" not in st.session_state:
    st.session_state.chat_display = []

# --- Pintar la conversación existente ---------------------------------------
for mensaje in st.session_state.chat_display:
    with st.chat_message(mensaje["role"]):
        st.markdown(mensaje["content"])

# --- Entrada del usuario -----------------------------------------------------
pregunta = st.chat_input("Escribe tu pregunta sobre paellas...")

if pregunta:
    st.session_state.chat_display.append({"role": "user", "content": pregunta})
    with st.chat_message("user"):
        st.markdown(pregunta)

    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            respuesta = base.ejecutar_agente(
                pregunta, st.session_state.api_historial, verbose=False
            )
        st.markdown(respuesta)

    st.session_state.chat_display.append({"role": "assistant", "content": respuesta})

with st.sidebar:
    st.subheader("Acerca de Paellero")
    st.markdown(
        "Agente de IA que calcula cantidades según tus recetas guardadas, "
        "ajusta el líquido según tu paella y tu fuego, y aprende de cada "
        "intento que le cuentes (valoración + notas)."
    )
    if st.button("🗑️ Borrar esta conversación"):
        st.session_state.api_historial = []
        st.session_state.chat_display = []
        st.rerun()
