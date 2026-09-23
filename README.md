# Plan de producción de centrales

API REST que calcula cuánta potencia tiene que producir cada central para cubrir la carga al menor coste. Python + FastAPI, escuchando en el puerto 8888.

## Cómo arrancarlo

Necesita Python 3.10 o superior.

Todos los comandos se ejecutan desde la carpeta de este proyecto, la que contiene `app`, `tests`, `example_payloads` y este README. Para situarte en ella, abre una terminal y usa `cd` con la ruta donde la hayas dejado:

```powershell
# Windows
cd "C:\ruta\hasta\powerplant-coding-challenge-master\solution"
```

```bash
# Linux / Mac
cd /ruta/hasta/powerplant-coding-challenge-master/solution
```

Para comprobar que estás en el sitio correcto, usa `dir` en Windows o `ls` en Linux/Mac: tienen que aparecer las carpetas `app`, `tests` y `example_payloads`.

En `example_payloads` están los payloads de ejemplo del enunciado, incluidos aquí para poder probar la API y lanzar los tests sin nada más.

El coste del CO2 en las centrales de gas (0,3 t por MWh) va **activado por defecto** en todos los sistemas. Al final de cada apartado se indica cómo desactivarlo.

### Windows (PowerShell o CMD)

Los comandos son los mismos en las dos terminales:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m app.main
```

El entorno solo hay que crearlo e instalarlo la primera vez. La aplicación queda arrancada y ocupa esa terminal mostrando los logs: cuando aparece `Uvicorn running on http://0.0.0.0:8888` ya está lista. Para pararla, `Ctrl+C`.

Tests (con la aplicación parada, o desde otra terminal):

```powershell
.venv\Scripts\python.exe -m pytest
```

Para probar la API, **abre una segunda terminal y sitúate en esta misma carpeta** con el mismo `cd` de antes, dejando la primera arrancada. Aquí sí cambia el comando según la terminal:

```powershell
# PowerShell
Invoke-RestMethod -Method Post -Uri http://localhost:8888/productionplan -ContentType "application/json" -InFile example_payloads\payload3.json
```

```bat
:: CMD
curl -X POST http://localhost:8888/productionplan -H "Content-Type: application/json" -d @example_payloads\payload3.json
```

Cambia el `3` por `1` o `2` para probar los otros payloads de ejemplo. También puedes abrir http://localhost:8888/docs en el navegador y lanzar la petición desde ahí.

Para arrancar sin CO2, ejecuta antes en la misma terminal `$env:INCLUDE_CO2="false"` en PowerShell, o `set INCLUDE_CO2=false` en CMD.

### Linux / Mac

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

Igual que en Windows: el entorno solo se crea la primera vez, y la aplicación se queda ocupando la terminal hasta que la pares con `Ctrl+C`.

Tests: `python -m pytest`

Para probar la API, **abre una segunda terminal en esta misma carpeta**, activa el entorno con `source .venv/bin/activate` y lanza:

```bash
curl -X POST http://localhost:8888/productionplan -H "Content-Type: application/json" -d @example_payloads/payload3.json
```

Para arrancar sin CO2: `INCLUDE_CO2=false python -m app.main`

## Enfoque

Primero calculo el coste por MWh de cada central: precio del combustible entre la eficiencia para gas y turbojet (más el CO2 en el gas) y 0 para la eólica. La eólica aquí no se puede modular, así que o va entera con lo que dé el viento o se apaga.

Rellenar la carga por orden de mérito no basta por culpa del pmin. En `payload2`, si pongo gasfiredbig1 a 460 me quedan 20 MW, pero gasfiredbig2 no puede bajar de 100. La respuesta buena es 380 + 100.

Por eso el algoritmo recorre las centrales por orden de mérito y decide para cada una si se enciende o no (búsqueda recursiva). Descarta una rama cuando:

- el pmin de lo que ya está encendido supera la carga (encender más solo lo empeora), o
- aunque encienda todo lo que queda, no llego a la carga.

Cuando ya está todo decidido, reparto la carga: cada central encendida arranca en su pmin y el resto va a las más baratas primero, hasta su pmax. Me quedo con el plan más barato, y si dos cuestan lo mismo, con el que enciende menos centrales.

Trabajo en décimas de MW como enteros, así la suma siempre cuadra con la carga y cada valor es múltiplo de 0,1.

Si ninguna combinación cuadra, la API devuelve 422 con el motivo. Un payload mal formado también da 422 y un error inesperado da 500. Cada petición queda en el log.

## Qué mejoraría

- **Rendimiento con muchas centrales.** La búsqueda es exponencial en el peor caso. Lo siguiente sería cortar una rama cuando su coste mínimo posible ya supera al mejor plan encontrado, y tratar las centrales idénticas (como gasfiredbig1 y gasfiredbig2) como un único grupo.
- **Modelo más realista.** Costes de arranque, rampas y varias horas a la vez en lugar de una.
- **Configuración y observabilidad.** Gestión de configuración más ordenada, logs estructurados y un endpoint de health.
- **Despliegue.** Empaquetarlo en un contenedor Docker.
