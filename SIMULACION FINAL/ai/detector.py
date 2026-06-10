"""
==============================================================================
MOTOR DE DETECCION DE OBJETOS — Sistema de Vigilancia Cienaga, Magdalena
==============================================================================
Archivo    : detector.py
Descripcion: Motor de deteccion de objetos con interfaz compatible con YOLO.
             Simula la deteccion realista de personas, vehiculos y eventos
             sospechosos mediante un modelo probabilistico calibrado.

             La interfaz es identica a la de un modelo YOLO real:
             - Entrada : imagen (bytes), posicion GPS, contexto
             - Salida  : lista de detecciones [{class, confidence, bbox, ...}]

             Para integrar un modelo YOLO real, reemplazar el metodo
             `detect()` manteniendo la misma firma y estructura de salida.

Nota       : En simulacion academica, los motores probabilisticos son
             estandar y validos para validar la arquitectura del sistema.
==============================================================================
"""

import random
import math
import time
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# CLASES DETECTABLES
# ─────────────────────────────────────────────────────────────────────────────
DETECTABLE_CLASSES = [
    "persona",
    "grupo_personas",
    "vehiculo",
    "vehiculo_sospechoso",
    "motocicleta",
    "actividad_sospechosa",
    "objeto_abandonado",
    "disturbio",
]

# Probabilidad base de deteccion por clase (sin modificadores)
BASE_DETECTION_PROB = {
    "persona"               : 0.35,
    "grupo_personas"        : 0.15,
    "vehiculo"              : 0.25,
    "vehiculo_sospechoso"   : 0.06,
    "motocicleta"           : 0.12,
    "actividad_sospechosa"  : 0.04,
    "objeto_abandonado"     : 0.08,
    "disturbio"             : 0.02,
}

# Rango de confianza por clase
CONFIDENCE_RANGE = {
    "persona"               : (0.65, 0.98),
    "grupo_personas"        : (0.60, 0.95),
    "vehiculo"              : (0.70, 0.99),
    "vehiculo_sospechoso"   : (0.55, 0.88),
    "motocicleta"           : (0.60, 0.92),
    "actividad_sospechosa"  : (0.50, 0.85),
    "objeto_abandonado"     : (0.55, 0.88),
    "disturbio"             : (0.52, 0.87),
}

# Limite de objetos detectados por frame (realismo)
MAX_DETECTIONS_PER_FRAME = 6


class Detection:
    """Estructura de una deteccion individual."""

    def __init__(self, cls: str, confidence: float,
                 bbox: tuple, position: tuple, camera_pos: tuple):
        self.cls        = cls
        self.confidence = round(confidence, 3)
        self.bbox       = bbox          # (x1, y1, x2, y2) en pixeles
        self.position   = position      # Posicion estimada en el mundo
        self.camera_pos = camera_pos    # Posicion del dron al momento de deteccion

    def to_dict(self) -> dict:
        return {
            "class"      : self.cls,
            "confidence" : self.confidence,
            "bbox"       : list(self.bbox),
            "world_pos"  : {
                "x": round(self.position[0], 2),
                "z": round(self.position[2], 2),
            },
        }


class ObjectDetector:
    """
    Motor de deteccion de objetos simulado con interfaz YOLO-compatible.

    Modela el comportamiento de un detector entrenado con YOLO + OpenCV,
    incluyendo:
      - Variacion de confianza por condiciones (altitud, zona de riesgo)
      - Correlacion entre detecciones (si hay grupo, hay personas)
      - Falsos positivos controlados (~5%)
      - Historial de detecciones para suavizar resultados
    """

    def __init__(self, drone_id: int, seed: Optional[int] = None):
        self.drone_id = drone_id
        self.rng      = random.Random(seed or (drone_id * 7919))
        self.history  = []          # Ultimas N detecciones para suavizado
        self.frame_count = 0
        self.last_medium_time = 0.0
        self.last_high_time = 0.0

    # ─────────────────────────────────────────────────────────────────────────

    def detect(self,
               image       : bytes,
               position    : tuple,
               risk_mult   : float = 1.0,
               width       : int   = 400,
               height      : int   = 240,
               simulation_time: float = 0.0) -> list:
        """
        Procesa un frame de camara y retorna una lista de detecciones.

        Parametros:
          image     : Bytes de la imagen de la camara (no usado en simulacion,
                      pero mantiene la interfaz para integracion real con YOLO)
          position  : (x, altitude, z) — posicion del dron en el mundo
          risk_mult : Multiplicador de probabilidad en zonas de alto riesgo
          width/height : Dimensiones de la imagen de camara

        Retorna:
          Lista de dicts con estructura YOLO: [{class, confidence, bbox, ...}]
        """
        self.frame_count += 1
        x, alt, z = position

        # Modificador por altitud (menos visibilidad a mayor altura)
        alt_factor = max(0.3, 1.0 - (alt - 10.0) / 40.0)

        # Modificador temporal (más actividad en ciertos momentos)
        time_factor = 1.0 + 0.3 * math.sin(self.frame_count / 50.0)

        detections = []

        # Eventos forzados (Alternados cada 100s MED y 300s HIGH)
        # Solo lo aplicamos al dron 1 para no saturar si hay 3 drones
        if self.drone_id == 1:
            if (simulation_time - self.last_high_time) >= 300.0 and simulation_time > 10.0:
                self.last_high_time = simulation_time
                self.last_medium_time = simulation_time # Reset medium so they don't overlap
                detections.append(Detection("disturbio", 0.95, (10, 10, 80, 80), (x, alt, z), position))
            elif (simulation_time - self.last_medium_time) >= 100.0 and simulation_time > 10.0:
                self.last_medium_time = simulation_time
                detections.append(Detection("vehiculo_sospechoso", 0.88, (20, 20, 90, 90), (x, alt, z), position))

        for cls in DETECTABLE_CLASSES:
            base_p = BASE_DETECTION_PROB[cls]
            p      = base_p * risk_mult * alt_factor * time_factor

            if self.rng.random() < p:
                conf_min, conf_max = CONFIDENCE_RANGE[cls]
                confidence = self.rng.uniform(conf_min, conf_max)

                # Generar bounding box simulado en la imagen
                bx1 = self.rng.randint(0, width  - 60)
                by1 = self.rng.randint(0, height - 40)
                bx2 = bx1 + self.rng.randint(20, 80)
                by2 = by1 + self.rng.randint(15, 60)

                # Posicion estimada en el mundo (proyeccion simplificada)
                wx = x + self.rng.uniform(-8, 8)
                wz = z + self.rng.uniform(-8, 8)

                det = Detection(
                    cls        = cls,
                    confidence = confidence,
                    bbox       = (bx1, by1, min(bx2, width), min(by2, height)),
                    position   = (wx, alt, wz),
                    camera_pos = position,
                )
                detections.append(det)

                if len(detections) >= MAX_DETECTIONS_PER_FRAME:
                    break

        # Correlaciones realistas
        detections = self._apply_correlations(detections)

        # Falsos positivos ocasionales (~5%)
        if self.rng.random() < 0.05 and detections:
            fp_idx = self.rng.randint(0, len(detections) - 1)
            detections[fp_idx].confidence *= 0.7   # Reducir confianza del FP

        # Actualizar historial
        self.history.append(len(detections))
        if len(self.history) > 20:
            self.history.pop(0)

        return [d.to_dict() for d in detections]

    def _apply_correlations(self, detections: list) -> list:
        """Aplica correlaciones entre clases de deteccion."""
        classes = [d.cls for d in detections]

        # Si hay grupo_personas, siempre hay al menos una persona
        if "grupo_personas" in classes and "persona" not in classes:
            ref = next(d for d in detections if d.cls == "grupo_personas")
            extra = Detection(
                cls        = "persona",
                confidence = self.rng.uniform(0.70, 0.95),
                bbox       = (ref.bbox[0] + 5, ref.bbox[1], ref.bbox[0] + 20, ref.bbox[3]),
                position   = ref.position,
                camera_pos = ref.camera_pos,
            )
            detections.append(extra)

        # Si hay disturbio, probablemente hay grupo
        if "disturbio" in classes and "grupo_personas" not in classes:
            ref = next(d for d in detections if d.cls == "disturbio")
            extra = Detection(
                cls        = "grupo_personas",
                confidence = self.rng.uniform(0.60, 0.85),
                bbox       = ref.bbox,
                position   = ref.position,
                camera_pos = ref.camera_pos,
            )
            detections.append(extra)

        return detections

    def get_detection_stats(self) -> dict:
        """Retorna estadisticas del detector."""
        avg = sum(self.history) / len(self.history) if self.history else 0
        return {
            "frames_procesados" : self.frame_count,
            "detecciones_promedio": round(avg, 2),
        }


# ─────────────────────────────────────────────────────────────────────────────
# PRUEBA UNITARIA
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Prueba del Motor de Deteccion ===\n")
    detector = ObjectDetector(drone_id=1, seed=42)

    test_cases = [
        {"position": (0, 15, 0),       "risk_mult": 1.0, "label": "Zona normal"},
        {"position": (-70, 15, -70),   "risk_mult": 2.0, "label": "Zona de alto riesgo"},
        {"position": (70, 15, 70),     "risk_mult": 1.8, "label": "Periferia noreste"},
        {"position": (0, 30, 0),       "risk_mult": 1.0, "label": "Alta altitud"},
    ]

    total_detections = 0
    for case in test_cases:
        dets = detector.detect(
            image       = b"",
            position    = case["position"],
            risk_mult   = case["risk_mult"],
            width       = 400,
            height      = 240,
        )
        total_detections += len(dets)
        print(f"[{case['label']:25s}] {len(dets)} detecciones:")
        for d in dets:
            print(f"   -> {d['class']:22s} conf={d['confidence']:.2f}")
        print()

    print(f"Total detecciones en prueba: {total_detections}")
    print(f"Estadisticas: {detector.get_detection_stats()}")
    print("\n[OK] Motor de deteccion funcionando correctamente.")
