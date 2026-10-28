# Paellero — agente de IA que aprende de cada paella

Agente manual (mismo patrón que Meteo) que te ayuda a planificar paellas usando
tus propios datos de curso, y que **recuerda cómo salió cada intento** para
afinar la próxima recomendación.

## ⚠️ Antes de nada: rellena tus datos

Tus PDFs de curso llevan avisos de copyright (uno es incluso un libro con ISBN
y todos los derechos reservados). Por eso estos ficheros vienen **vacíos, con
solo un par de ejemplos de muestra** — eres tú quien transcribe, en tus propias
palabras, los datos que quieras usar:

- **`arroces.json`** — una entrada por variedad de arroz (absorción, minutos
  de apertura, resistencia a la sobrecocción, notas tuyas).
- **`recetas.json`** — una entrada por receta (ingredientes para X raciones +
  pasos). Borra los ejemplos (`ejemplo_bomba`, `ejemplo_paella_valenciana`)
  cuando metas los tuyos, o déjalos como referencia de formato.

No hace falta copiar frases enteras de los PDFs: con los números y una
descripción corta tuya es más que suficiente para que el agente funcione bien.

## Cómo funciona la "memoria" entre paellas

El agente no se reentrena solo — lo que hace es **guardar cada intento** en
`historial_paellas.json` (fecha, receta, raciones, valoración 1-5, qué
cambiaste, notas) y **leer ese historial antes de recomendar**, para que
tenga en cuenta lo que pasó la última vez. Es memoria persistente real, no
aprendizaje del modelo en sí.

Ejemplo de conversación:
```
Tú: Voy a hacer la paella valenciana para 6 personas
Paellero: [consulta historial → ve que la última vez (nota 3/5) anotaste
           "quedó soso, subir pimentón"]
           Aquí tienes las cantidades para 6 raciones... Como la última vez
           anotaste que quedó soso, te subo el pimentón de 3.75g a 4.5g...

Tú: Me ha salido genial, le puse un poco más de azafrán también
Paellero: [registra el resultado con valoración y notas]
           Genial, lo he guardado. La próxima vez ya partiremos de este punto.
```

## Puesta en marcha

1. Copia esta carpeta junto a tu proyecto `meteo-agent` (o donde prefieras).
2. Si ya tienes un `.venv` con `openai` y `python-dotenv` instalados (del
   proyecto Meteo), puedes reutilizarlo. Si no:
   ```bash
   python -m venv .venv
   .venv\Scripts\Activate.ps1      # Windows
   pip install -r requirements.txt
   ```
3. Copia `.env.example` a `.env` y pega tu API key (la misma que ya creaste
   para Meteo sirve).
4. Rellena `arroces.json` y `recetas.json` con tus datos.
5. Ejecuta:
   ```bash
   python paella_agent.py
   ```

## Ficheros

| Fichero | Qué contiene |
|---|---|
| `arroces.json` | Variedades de arroz y sus características (lo rellenas tú) |
| `recetas.json` | Recetas base, ingredientes y pasos (lo rellenas tú) |
| `historial_paellas.json` | Se crea solo la primera vez que registras un resultado — tu historial de intentos |
| `paella_agent.py` | El agente: tools + bucle + memoria |

## Versión con el OpenAI Agents SDK

`paella_agent_sdk.py` es la misma lógica de datos (recetas, arroces, equipo,
historial), pero conectada al modelo con el SDK en vez de con el bucle
programado a mano. Para usarla:

```bash
pip install -r requirements.txt   # ya incluye openai-agents
python paella_agent_sdk.py
```

Diferencias respecto a `paella_agent.py`:
- Las tools se definen con `function_tool(...)` en vez de escribir a mano
  la ficha JSON Schema de cada una — el SDK la genera sola a partir de los
  type hints y el docstring de la función.
- El bucle pensar→actuar→observar→repetir lo gestiona `Runner.run`, no un
  `for` escrito por nosotros.
- La conversación se guarda con `SQLiteSession` en `paellero_sesion.db`: si
  cierras el programa y lo vuelves a abrir, recuerda de qué hablasteis antes
  (esto es memoria de **conversación**, distinta de `historial_paellas.json`,
  que es memoria de **resultados de paellas** y sigue funcionando igual).

Las dos versiones comparten los mismos ficheros de datos (`arroces.json`,
`recetas.json`, `equipo.json`, `historial_paellas.json`): puedes usar la que
prefieras, o alternar entre ellas, sin que se pisen los datos.

## Compartir por internet (gratis, con Streamlit)

`app.py` es una interfaz web de chat para el mismo agente. Para probarla en
tu propio ordenador primero:

```bash
pip install -r requirements.txt   # ya incluye streamlit
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edita .streamlit/secrets.toml y pon tu API key real
streamlit run app.py
```

Se abrirá en `http://localhost:8501`. Si funciona ahí, ya puedes desplegarla:

### Pasos para publicarla gratis

1. **Sube el proyecto a GitHub** (puede ser un repositorio privado):
   - Crea un repositorio nuevo en [github.com](https://github.com).
   - Desde la terminal, dentro de la carpeta del proyecto:
     ```bash
     git init
     git add .
     git commit -m "Paellero"
     git branch -M main
     git remote add origin https://github.com/TU_USUARIO/paellero.git
     git push -u origin main
     ```
   - Como `.env` y `.streamlit/secrets.toml` están en `.gitignore`, tu API key
     **no se sube** al repositorio — eso es justo lo que queremos.

2. **Despliega en Streamlit Community Cloud** (gratis):
   - Ve a [share.streamlit.io](https://share.streamlit.io) e inicia sesión con
     tu cuenta de GitHub.
   - "New app" → selecciona tu repositorio, la rama `main` y el fichero
     `app.py`.
   - En **Settings → Secrets**, pega el contenido de tu `secrets.toml` real
     (con tu API key). Esto es equivalente a tu fichero local, pero solo lo
     ve el hosting, nunca aparece en el código.
   - Dale a "Deploy". En un par de minutos tendrás una URL pública tipo
     `https://tu-app.streamlit.app` para compartir con quien quieras.

### Cosas a tener en cuenta

- **Gasto compartido**: todo el que use la URL consume tu saldo de API. Si la
  vas a compartir con más gente, pon un límite de gasto mensual en
  `platform.openai.com/settings/organization/billing` para evitar sorpresas.
- **Datos compartidos**: `historial_paellas.json` y `equipo.json` son
  ficheros únicos — todas las personas que usen la app leen y escriben en el
  mismo cuaderno de recetas y resultados. Si quieres que cada persona tenga
  su propio historial, se puede añadir más adelante (por ejemplo, pidiendo un
  nombre de usuario y guardando un fichero distinto por persona).
- **Almacenamiento no garantizado a largo plazo**: en el plan gratuito de
  Streamlit Cloud, el disco puede reiniciarse si la app se redespliega o
  lleva un tiempo sin uso. Para un grupo pequeño de amigos/familia suele ir
  bien, pero si necesitas que el historial persista de forma garantizada,
  habría que moverlo a una base de datos externa (fuera del alcance de esta
  versión).
