"""
==============================================================================
CLASIFICADOR DE RIESGO — Sistema de Vigilancia Cienaga, Magdalena
==============================================================================
Archivo    : classifier.py
Descripcion: Clasifica eventos detectados en niveles de riesgo
             (LOW / MEDIUM / HIGH) usando un motor de reglas + puntaje
             ponderado, que replica el comportamiento de un clasificador
             ML entrenado (compatible con scikit-learn / TensorFlow).

             La arquitectura permite sustituir el motor de reglas por un
             modelo ML real manteniendo la misma firma de entrada/salida.

Niveles    :
  LOW    — Actividad normal (transito, personas caminando)
  MEDIUM — Situacion inusual que requiere atencion (aglomeracion, veh. detenido)
  HIGH   — Evento critico que requiere respuesta inmediata (disturbio, robo)
==============================================================================
"""

import math
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# PUNTAJES BASE POR CLASE DE DETECCION
# ─────────────────────────────────────────────────────────────────────────────
CLASS_SCORES = {
    "persona"               : 1,
    "grupo_personas"        : 3,
    "vehiculo"              : 1,
    "vehiculo_sospechoso"   : 4,
    "motocicleta"           : 2,
    "actividad_sospechosa"  : 6,
    "objeto_abandonado"     : 3,
    "disturbio"             : 8,
}

# Umbral de puntaje para clasificacion
THRESHOLD_MEDIUM = 4
THRESHOLD_HIGH   = 8

# Multiplicador nocturno (horas 20:00-06:00 en tiempo de simulacion)
NIGHT_MULTIPLIER = 1.5

# Horario de simulacion base (segundos de simulacion => hora del dia)
SIM_SECONDS_PER_HOUR = 120.0   # 120 segundos de simulacion = 1 hora del dia


# ─────────────────────────────────────────────────────────────────────────────
# TABLAS DE DESCRIPCION
# ─────────────────────────────────────────────────────────────────────────────
RISK_DESCRIPTIONS = {
    "LOW": [
        "Transito normal de personas",
        "Actividad cotidiana en la via publica",
        "Vehiculo circulando normalmente",
        "Persona caminando por zona comun",
    ],
    "MEDIUM": [
        "Aglomeracion inusual de personas detectada",
        "Vehiculo detenido en zona de alta circulacion",
        "Grupo numeroso en horario nocturno",
        "Permanencia prolongada en zona semi-restringida",
        "Motocicleta con comportamiento irregular",
        "Objeto sospechoso detectado en via publica",
    ],
    "HIGH": [
        "Disturbio o altercado detectado — Respuesta requerida",
        "Actividad sospechosa en zona de alto riesgo — Alerta maxima",
        "Posible acto vandálico detectado",
        "Comportamiento agresivo identificado por camara",
        "Vehiculo sospechoso en zona critica — Seguimiento activado",
        "Aglomeracion violenta detectada — Notificando autoridades",
    ],
}


class RiskClassifier:
    """
    Clasificador de nivel de riesgo basado en motor de reglas ponderadas.

    Arquitectura:
      1. Calcular puntaje total ponderado por clase y confianza
      2. Aplicar modificadores contextuales (zona, hora, historial)
      3. Clasificar segun umbrales calibrados
      4. Generar descripcion textual del evento

    Para integrar un modelo ML real (scikit-learn / TF), reemplazar
    el metodo `classify()` manteniendo la misma firma.
    """

    def __init__(self):
        self.event_history   = []    # Historial de clasificaciones
        self.consecutive_high = 0    # Alertas HIGH consecutivas (escalada)

    # ─────────────────────────────────────────────────────────────────────────

    def classify(self,
                 detections     : list,
                 position       : tuple,
                 drone_id       : int,
                 simulation_time: float,
                 risk_zone      : Optional[dict] = None) -> dict:
        """
        Clasifica un conjunto de detecciones en un nivel de riesgo.

        Parametros:
          detections      : Lista de dicts de detecciones (output de ObjectDetector)
          position        : (x, altitude, z) del dron
          drone_id        : ID del dron que realizo la deteccion
          simulation_time : Tiempo de simulacion en segundos
          risk_zone       : Dict de zona de riesgo si aplica, o None

        Retorna:
          dict con: risk_level, score, description, detections, metadata
        """
        if not detections:
            return self._make_result("LOW", 0, "Sin detecciones relevantes", detections, position)

        # ── 1. Calcular puntaje base ─────────────────────────────────────────
        score = 0.0
        for det in detections:
            cls  = det.get("class", "persona")
            conf = det.get("confidence", 0.5)
            base = CLASS_SCORES.get(cls, 1)
            score += base * conf

        # ── 2. Modificadores contextuales ────────────────────────────────────

        # Hora del dia (simulada)
        hour_of_day = (simulation_time / SIM_SECONDS_PER_HOUR) % 24
        is_night    = (hour_of_day >= 20 or hour_of_day < 6)
        if is_night:
            score *= NIGHT_MULTIPLIER

        # Zona de riesgo
        if risk_zone:
            score *= risk_zone.get("risk_multiplier", 1.0)

        # Numero de detecciones (densidad)
        n_dets = len(detections)
        if n_dets >= 4:
            score *= 1.3
        elif n_dets >= 2:
            score *= 1.1

        # Historial: si hubo HIGH reciente, umbral mas sensible
        if self.consecutive_high >= 2:
            score *= 1.2

        # ── 3. Clasificar ────────────────────────────────────────────────────
        if score >= THRESHOLD_HIGH:
            risk_level = "HIGH"
            self.consecutive_high += 1
        elif score >= THRESHOLD_MEDIUM:
            risk_level = "MEDIUM"
            self.consecutive_high = 0
        else:
            risk_level = "LOW"
            self.consecutive_high = 0

        # ── 4. Descripcion del evento ─────────────────────────────────────────
        description = self._generate_description(
            risk_level, detections, is_night, risk_zone
        )

        # ── 5. Registrar en historial ─────────────────────────────────────────
        event = {
            "risk_level"     : risk_level,
            "score"          : round(score, 2),
            "sim_time"       : simulation_time,
            "drone_id"       : drone_id,
        }
        self.event_history.append(event)
        if len(self.event_history) > 100:
            self.event_history.pop(0)

        return self._make_result(risk_level, score, description, detections, position,
                                 metadata={
                                     "is_night"   : is_night,
                                     "hour_approx": round(hour_of_day, 1),
                                     "in_risk_zone": risk_zone["name"] if risk_zone else None,
                                     "n_detections": n_dets,
                                     "score_raw"  : round(score, 2),
                                 })

    # ─────────────────────────────────────────────────────────────────────────

    def _generate_description(self, risk_level: str, detections: list,
                               is_night: bool, risk_zone: Optional[dict]) -> str:
        """Genera una descripcion textual del evento."""
        import random
        rng = random.Random(len(detections) + int(is_night))

        base = rng.choice(RISK_DESCRIPTIONS[risk_level])

        # Enriquecer con contexto
        extras = []
        classes = [d.get("class", "") for d in detections]

        if "grupo_personas" in classes:
            count = sum(1 for c in classes if "persona" in c)
            extras.append(f"~{max(3, count*2)} personas")
        if "vehiculo_sospechoso" in classes:
            extras.append("vehiculo con placa cubierta")
        if is_night:
            extras.append("horario nocturno")
        if risk_zone:
            extras.append(f"zona: {risk_zone['name']}")

        if extras:
            return f"{base} ({', '.join(extras)})"
        return base

    def _make_result(self, risk_level: str, score: float, description: str,
                     detections: list, position: tuple, metadata: dict = None) -> dict:
        """Construye el dict de resultado estandarizado."""
        x, alt, z = position
        return {
            "risk_level"  : risk_level,
            "score"       : round(score, 2),
            "description" : description,
            "detections"  : detections,
            "position"    : {"x": round(x, 2), "z": round(z, 2), "alt": round(alt, 2)},
            "metadata"    : metadata or {},
        }

    def get_stats(self) -> dict:
        """Retorna estadisticas del clasificador."""
        if not self.event_history:
            return {"total": 0, "por_nivel": {}}
        counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
        for e in self.event_history:
            counts[e["risk_level"]] = counts.get(e["risk_level"], 0) + 1
        return {
            "total"          : len(self.event_history),
            "por_nivel"      : counts,
            "ratio_alto_riesgo": round(
                (counts["MEDIUM"] + counts["HIGH"]) / len(self.event_history), 3
            ),
        }


# ─────────────────────────────────────────────────────────────────────────────
# PRUEBA UNITARIA
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Prueba del Clasificador de Riesgo ===\n")
    clf = RiskClassifier()

    test_cases = [
        {
            "label": "Caso 1 — Persona ingresando zona restringida",
            "detections": [
                {"class": "persona",           "confidence": 0.88, "bbox": [10, 20, 50, 80]},
                {"class": "actividad_sospechosa", "confidence": 0.72, "bbox": [15, 25, 55, 85]},
            ],
            "position"    : (-70, 15, 20),
            "sim_time"    : 150,
            "risk_zone"   : {"name": "Bodega_Abandonada", "risk_multiplier": 2.5},
        },
        {
            "label": "Caso 2 — Grupo numeroso en horario nocturno",
            "detections": [
                {"class": "grupo_personas",    "confidence": 0.82, "bbox": [0, 0, 100, 100]},
                {"class": "persona",           "confidence": 0.90, "bbox": [5, 5, 30, 60]},
                {"class": "persona",           "confidence": 0.85, "bbox": [60, 5, 90, 60]},
            ],
            "position"    : (0, 15, 0),
            "sim_time"    : 2520,    # => hora 21:00 (nocturno)
            "risk_zone"   : None,
        },
        {
            "label": "Caso 3 — Vehiculo detenido en zona critica",
            "detections": [
                {"class": "vehiculo_sospechoso", "confidence": 0.79, "bbox": [50, 30, 150, 90]},
                {"class": "persona",             "confidence": 0.70, "bbox": [100, 40, 130, 80]},
            ],
            "position"    : (-70, 15, -70),
            "sim_time"    : 60,
            "risk_zone"   : {"name": "Callejon_Suroeste", "risk_multiplier": 2.0},
        },
        {
            "label": "Caso 4 — Transito normal diurno",
            "detections": [
                {"class": "persona",   "confidence": 0.91, "bbox": [20, 10, 60, 70]},
                {"class": "vehiculo",  "confidence": 0.87, "bbox": [80, 30, 180, 90]},
            ],
            "position"    : (20, 15, -20),
            "sim_time"    : 480,    # => hora 04:00 (diurno temprano)
            "risk_zone"   : None,
        },
    ]

    for case in test_cases:
        result = clf.classify(
            detections      = case["detections"],
            position        = case["position"],
            drone_id        = 1,
            simulation_time = case["sim_time"],
            risk_zone       = case.get("risk_zone"),
        )
        level = result["risk_level"]
        emoji = {"LOW": "[BAJO]", "MEDIUM": "[MEDIO]", "HIGH": "[ALTO] "}.get(level, "[?????]")
        print(f"{emoji} {case['label']}")
        print(f"   Nivel    : {level} (score={result['score']})")
        print(f"   Descripcion: {result['description']}")
        print(f"   Metadata : {result['metadata']}")
        print()

    print(f"Estadisticas finales: {clf.get_stats()}")
    print("\n[OK] Clasificador de riesgo funcionando correctamente.")
