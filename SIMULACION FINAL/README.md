# Sistema Inteligente de Vigilancia con Drones
## Ciénaga, Magdalena — Simulación Webots R2025a

<div align="center">

```
 ██████╗ ██╗███████╗███╗   ██╗ █████╗  ██████╗  █████╗ 
██╔════╝ ██║██╔════╝████╗  ██║██╔══██╗██╔════╝ ██╔══██╗
██║      ██║█████╗  ██╔██╗ ██║███████║██║  ███╗███████║
██║      ██║██╔══╝  ██║╚██╗██║██╔══██║██║   ██║██╔══██║
╚██████╗ ██║███████╗██║ ╚████║██║  ██║╚██████╔╝██║  ██║
 ╚═════╝ ╚═╝╚══════╝╚═╝  ╚═══╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝
```

**Sistema de Vigilancia Inteligente con Drones Autónomos**

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Webots](https://img.shields.io/badge/Webots-R2025a-green)
![IA](https://img.shields.io/badge/IA-Detector%20%2B%20Clasificador-orange)
![Estado](https://img.shields.io/badge/Estado-Simulaci%C3%B3n%20Activa-brightgreen)

</div>

---

## 📋 Descripción

Este proyecto implementa una simulación completa en **Webots R2025a** de un sistema de drones autónomos para vigilancia ciudadana en **Ciénaga, Magdalena**. El sistema combina robótica autónoma, inteligencia artificial y visión por computadora para monitorear un entorno urbano y detectar eventos sospechosos.

### Características principales

- 🛸 **3 Drones Mavic 2 Pro** con patrullaje autónomo por zonas
- 🧠 **Motor de detección IA** con interfaz compatible con YOLO
- 📊 **Clasificador de riesgo** (LOW / MEDIUM / HIGH)
- 🖥️ **Dashboard en tiempo real** con mapa 2D y panel de alertas
- 📁 **Generación automática de reportes** JSON
- 📡 **Comunicación bidireccional** dron ↔ Centro de Control

---

## 🏗️ Estructura del Proyecto

```
Proyecto_Drones_Cienaga/
│
├── worlds/
│   └── cienaga.wbt              # Mundo urbano de Ciénaga (Webots R2025a)
│
├── controllers/
│   ├── drone_controller/
│   │   └── drone_controller.py  # Controlador autónomo del dron
│   └── control_center/
│       └── control_center.py    # Supervisor del Centro de Control
│
├── ai/
│   ├── detector.py              # Motor de detección (interfaz YOLO)
│   └── classifier.py           # Clasificador de nivel de riesgo
│
├── monitor/
│   └── dashboard.py            # Dashboard de monitoreo en tiempo real
│
├── reports/                    # Reportes generados automáticamente
│   ├── shared_state.json       # Estado compartido en tiempo real
│   └── reporte_sesion_*.json   # Reportes por sesión
│
├── assets/
│   ├── edificios/
│   ├── calles/
│   └── drones/
│
└── README.md
```

---

## ⚙️ Requisitos

### Software

| Herramienta | Versión mínima | Notas |
|-------------|---------------|-------|
| Webots      | R2025a        | [Descargar aquí](https://cyberbotics.com) |
| Python      | 3.10+         | Incluido con Webots |
| tkinter     | Estándar      | Incluido con Python |

### No se requieren librerías adicionales
El proyecto usa únicamente la API estándar de Webots y módulos de la biblioteca estándar de Python (`json`, `math`, `random`, `tkinter`, `pathlib`).

---

## 🚀 Instrucciones de Ejecución

### 1. Abrir la simulación en Webots

```bash
# Abrir Webots y cargar el mundo
Archivo → Abrir... → worlds/cienaga.wbt
```

O desde línea de comandos:
```powershell
webots "worlds\cienaga.wbt"
```

### 2. Iniciar la simulación

1. En Webots, presionar el botón **Play** ▶
2. Los 3 drones despegarán automáticamente y comenzarán el patrullaje
3. El Centro de Control comenzará a recibir mensajes

### 3. Abrir el Dashboard (en otra terminal)

```powershell
# Desde la raíz del proyecto
python monitor\dashboard.py
```

El dashboard se actualizará automáticamente cada 500ms leyendo el archivo `reports/shared_state.json`.

### 4. Ver los reportes generados

Los reportes se generan automáticamente en la carpeta `reports/`:
- `shared_state.json` — Estado en tiempo real
- `alerta_HIGH_drone1_*.json` — Evidencias de alertas
- `reporte_sesion_*.json` — Reportes periódicos de sesión

---

## 🏙️ Descripción del Entorno

El mundo `cienaga.wbt` representa una sección urbana de Ciénaga con:

| Elemento | Ubicación | Descripción |
|----------|-----------|-------------|
| Parque Central | (0, 0) | Centro de la ciudad |
| Zona Residencial | Cuadrantes Norte | Viviendas 1-2 pisos |
| Colegio | (55, 55) | Institución educativa |
| Zona Comercial | (20-50, -20) | Locales y supermercado |
| Estación de Policía | (-55, -25) | Con torre de comunicación |
| Centro de Monitoreo | (0, -60) | Con antena |
| Zona de Riesgo 1 | (-70, -70) | Callejón suroeste |
| Zona de Riesgo 2 | (70, 70) | Periferia noreste |
| Zona de Riesgo 3 | (-70, 20) | Bodega abandonada |

---

## 🛸 Rutas de Patrullaje

Cada dron cubre una zona específica de la ciudad:

```
Drone 1 (Azul)   → Zona Norte/Este  → 11 waypoints
Drone 2 (Naranja) → Zona Sur/Oeste  → 11 waypoints  
Drone 3 (Morado) → Zona Central     → 11 waypoints
```

**Altitud de vuelo:** 15 metros  
**Velocidad:** ~4 m/s horizontal

---

## 🧠 Sistema de Inteligencia Artificial

### Detector de Objetos (`ai/detector.py`)

Motor probabilístico con interfaz compatible con YOLO v8:

| Clase | Probabilidad Base | Rango Confianza |
|-------|-----------------|-----------------|
| `persona` | 35% | 0.65 – 0.98 |
| `grupo_personas` | 15% | 0.60 – 0.95 |
| `vehiculo` | 25% | 0.70 – 0.99 |
| `vehiculo_sospechoso` | 6% | 0.55 – 0.88 |
| `actividad_sospechosa` | 4% | 0.50 – 0.85 |
| `disturbio` | 2% | 0.52 – 0.87 |

**Modificadores:** zona de riesgo (×1.8–2.5), altitud, hora del día

### Clasificador de Riesgo (`ai/classifier.py`)

| Nivel | Umbral de Puntaje | Ejemplos |
|-------|-----------------|---------|
| 🟢 LOW | < 4 pts | Tránsito normal, personas caminando |
| 🟡 MEDIUM | 4 – 7 pts | Aglomeración inusual, vehículo detenido |
| 🔴 HIGH | ≥ 8 pts | Disturbio, actividad sospechosa en zona crítica |

**Modificadores contextuales:**
- Horario nocturno (20:00–06:00): ×1.5
- Zona de alto riesgo: ×1.8 – 2.5
- Densidad de detecciones (≥4 objetos): ×1.3

---

## 📡 Protocolo de Comunicación

### Mensaje de Estado (Dron → Centro)

```json
{
  "type": "STATUS",
  "drone_id": 1,
  "zone": "norte",
  "position": {"x": 15.2, "y": 15.0, "z": 22.1},
  "state": "PATROL",
  "altitude": 15.0,
  "total_dist_m": 125.3,
  "alerts_sent": 2,
  "sim_time": 45.6
}
```

### Mensaje de Alerta (Dron → Centro)

```json
{
  "type": "ALERT",
  "drone_id": 1,
  "alert": {
    "risk_level": "HIGH",
    "score": 12.4,
    "description": "Disturbio detectado (zona: Bodega_Abandonada, horario nocturno)",
    "detections": [
      {"class": "disturbio", "confidence": 0.82, "bbox": [...]},
      {"class": "grupo_personas", "confidence": 0.75, "bbox": [...]}
    ]
  }
}
```

### Comando del Centro (Centro → Dron)

```json
{"action": "HOVER", "reason": "Alerta HIGH detectada"}
{"action": "GOTO",  "x": -70, "z": 20}
{"action": "RESUME"}
```

---

## 🧪 Casos de Prueba

### Caso 1 — Persona en zona restringida (Bodega Abandonada)

**Condición:** Drone 1 sobrevuela (-70, 20) — Zona de riesgo 3  
**Multiplicador de riesgo:** 2.5  
**Resultado esperado:** Alerta `HIGH` con descripción de actividad sospechosa  
**Respuesta del sistema:** Centro envía comando `HOVER` al dron

### Caso 2 — Grupo numeroso en horario nocturno

**Condición:** t_sim > 2400s (hora simulada ≈ 20:00), grupo detectado  
**Modificador nocturno:** ×1.5  
**Resultado esperado:** Clasificación `MEDIUM` o `HIGH`  
**Respuesta:** Alerta registrada con timestamp y evidencia JSON

### Caso 3 — Vehículo sospechoso en callejón suroeste

**Condición:** Drone 2 sobrevuela (-70, -70) — Zona de riesgo 1  
**Multiplicador:** 2.0  
**Resultado esperado:** Seguimiento (waypoint insertado automáticamente) + alerta `HIGH`

---

## 🔧 Pruebas Unitarias de los Módulos IA

```powershell
# Probar el detector de objetos
python ai\detector.py

# Probar el clasificador de riesgo
python ai\classifier.py

# Abrir el dashboard independientemente
python monitor\dashboard.py
```

---

## 📈 Resultados Esperados

Tras una sesión de simulación de 5 minutos:

- ✅ Los 3 drones completan múltiples ciclos de patrullaje
- ✅ Se generan 5–15 alertas MEDIUM y 2–5 alertas HIGH
- ✅ El dashboard muestra trails de los drones en tiempo real
- ✅ Los reportes JSON se guardan automáticamente cada 30s
- ✅ Las evidencias de alertas HIGH se almacenan individualmente

---

## 🔮 Mejoras Futuras

- [ ] Integración con YOLO v8 real para detección en imágenes Webots
- [ ] Reconocimiento de matrículas de vehículos
- [ ] Coordinación multi-dron (cobertura sin solapamiento)
- [ ] Predicción de zonas de riesgo con ML temporal
- [ ] Integración con cámaras de seguridad terrestres (RTSP)
- [ ] Reconocimiento facial con base de datos de personas buscadas
- [ ] Notificaciones móviles a patrullas policiales

---

## 👥 Equipo

**Proyecto:** Sistema Inteligente de Vigilancia con Drones  
**Ciudad:** Ciénaga, Magdalena, Colombia  
**Simulador:** Webots R2025a  
**Lenguaje:** Python 3.10+

---

## 📄 Licencia

Este proyecto es de uso académico. Los módulos de IA y el controlador del dron pueden adaptarse para simulaciones reales con las modificaciones indicadas en el código.

---

<div align="center">
<em>Desarrollado con Webots R2025a · Python · Inteligencia Artificial · Visión por Computadora</em>
</div>
