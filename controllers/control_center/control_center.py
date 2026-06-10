"""
==============================================================================
CENTRO DE CONTROL — Sistema de Vigilancia con Drones Cienaga, Magdalena
==============================================================================
Archivo    : control_center.py
Descripcion: Supervisor Webots que actua como Centro de Monitoreo Central.
             Recibe mensajes de todos los drones, los registra, genera
             reportes JSON y guarda evidencias de alertas.

Tipo       : Robot Supervisor en Webots R2025a
==============================================================================
"""

import sys
import os
import json
import math
from datetime import datetime
from pathlib import Path

from controller import Supervisor, Receiver, Emitter

# ─────────────────────────────────────────────────────────────────────────────
# RUTAS DEL PROYECTO
# ─────────────────────────────────────────────────────────────────────────────
PROJECT_ROOT  = Path(__file__).resolve().parents[2]
REPORTS_DIR   = PROJECT_ROOT / "reports"
SHARED_STATE  = PROJECT_ROOT / "reports" / "shared_state.json"
COMMANDS_FILE = PROJECT_ROOT / "reports" / "commands.json"

REPORTS_DIR.mkdir(exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# COLORES CONSOLA (Windows compatible via simple prefijos)
# ─────────────────────────────────────────────────────────────────────────────
RISK_COLORS = {
    "LOW"    : "[ OK  ]",
    "MEDIUM" : "[WARN ]",
    "HIGH"   : "[ALERT]",
}


class ControlCenter:
    """Centro de Control Central — supervisa todos los drones."""

    def __init__(self):
        self.robot    = Supervisor()
        self.timestep = int(self.robot.getBasicTimeStep())

        # ── Comunicacion ──────────────────────────────────────────────────────
        self.receiver = self.robot.getDevice("receptor_central")
        self.receiver.enable(self.timestep)
        self.emitter  = self.robot.getDevice("emisor_central")

        # ── Estado del sistema ────────────────────────────────────────────────
        self.drone_states    = {}    # {drone_id: ultimo_status}
        self.alert_log       = []    # Lista de todas las alertas
        self.total_messages  = 0
        self.session_start   = datetime.now()
        self.last_report_time = 0.0
        self.report_interval  = 30.0   # segundos de simulacion entre reportes
        self.active_alerts   = {}      # {drone_id: {"state": str, "timer_start": float}}

        print("=" * 60)
        print(" CENTRO DE CONTROL — Cienaga Drone Surveillance System")
        print(f" Inicio de sesion: {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        # Escribir estado inicial
        self._write_shared_state()

    # ─────────────────────────────────────────────────────────────────────────
    # PROCESAMIENTO DE MENSAJES
    # ─────────────────────────────────────────────────────────────────────────

    def _process_incoming(self):
        """Lee todos los mensajes disponibles en la cola."""
        while self.receiver.getQueueLength() > 0:
            try:
                raw     = self.receiver.getString()
                payload = json.loads(raw)
                self._handle_message(payload)
            except Exception as e:
                print(f"[CentroControl] Error procesando mensaje: {e}")
            finally:
                self.receiver.nextPacket()

    def _handle_message(self, payload: dict):
        """Procesa un mensaje recibido de un dron."""
        msg_type = payload.get("type", "STATUS")
        drone_id = payload.get("drone_id", 0)
        self.total_messages += 1

        # Actualizar estado del dron
        self.drone_states[drone_id] = payload

        if msg_type == "ALERT":
            self._handle_alert(payload)
        else:
            sim_time = payload.get("sim_time", 0)
            pos      = payload.get("position", {})
            state    = payload.get("state", "?")
            # Log periodico (cada N mensajes para no saturar la consola)
            if self.total_messages % 10 == 0:
                print(f"[CC] Drone {drone_id} | t={sim_time:.0f}s | "
                      f"Estado={state} | "
                      f"Pos=({pos.get('x',0):.1f}, {pos.get('z',0):.1f}) | "
                      f"Alt={pos.get('y',0):.1f}m")

    def _handle_alert(self, payload: dict):
        """Procesa una alerta de riesgo recibida de un dron."""
        alert    = payload.get("alert", {})
        drone_id = payload.get("drone_id", 0)
        pos      = payload.get("position", {})
        sim_time = payload.get("sim_time", 0)

        risk_level  = alert.get("risk_level", "LOW")
        description = alert.get("description", "")
        detections  = alert.get("detections", [])

        label = RISK_COLORS.get(risk_level, "[?????]")

        print(f"\n{'='*60}")
        print(f" {label} ALERTA NIVEL {risk_level} — Drone {drone_id}")
        print(f" Descripcion : {description}")
        print(f" Posicion    : X={pos.get('x',0):.1f} Z={pos.get('z',0):.1f} Y={pos.get('y',0):.1f}m")
        print(f" Tiempo sim. : {sim_time:.1f} s")
        print(f" Detecciones : {len(detections)} objeto(s)")
        for det in detections:
            print(f"   - {det.get('class','?'):15s} conf={det.get('confidence',0):.2f}")
        print(f"{'='*60}\n")

        # Registrar en log
        alert_entry = {
            "timestamp"   : datetime.now().isoformat(),
            "sim_time"    : sim_time,
            "drone_id"    : drone_id,
            "zone"        : payload.get("zone", ""),
            "risk_level"  : risk_level,
            "description" : description,
            "position"    : pos,
            "detections"  : detections,
        }
        self.alert_log.append(alert_entry)

        # Guardar evidencia individual
        self._save_alert_evidence(alert_entry)

        # Actualizar estado compartido para el dashboard
        self._write_shared_state()

        # Responder al dron si es HIGH
        if risk_level == "HIGH":
            self._dispatch_response(drone_id, alert_entry)

    def _dispatch_response(self, drone_id: int, alert: dict):
        """Envia comando de respuesta al dron en caso de alerta HIGH y registra la intervencion."""
        if drone_id not in self.active_alerts:
            self._dispatch_command(drone_id, "HOVER", f"Alerta HIGH detectada — {alert.get('description','')}")
            self.active_alerts[drone_id] = {
                "state": "HOVER", 
                "timer_start": self.robot.getTime()
            }

    def _dispatch_command(self, drone_id: int, action: str, reason: str):
        cmd = {
            "action"    : action,
            "reason"    : reason,
            "target_drone": drone_id,
        }
        try:
            msg = json.dumps(cmd)
            self.emitter.send(msg.encode("utf-8"))
            print(f"[CC] Comando {action} enviado a Drone {drone_id}: {reason}")
        except Exception as e:
            print(f"[CC] Error enviando comando: {e}")

    def _manage_interventions(self, sim_time: float):
        for drone_id, data in list(self.active_alerts.items()):
            state = data["state"]
            start_time = data["timer_start"]
            
            if state == "HOVER":
                # Simular 10 segundos de atencion a la alerta (tomando fotos, etc)
                if sim_time - start_time >= 10.0:
                    self._dispatch_command(drone_id, "RESUME", "Alerta atendida. Retomando patrullaje.")
                    data["state"] = "PATROL_AFTER_ALERT"
                    data["timer_start"] = sim_time
            elif state == "PATROL_AFTER_ALERT":
                # Patrullar por 100 segundos
                if sim_time - start_time >= 100.0:
                    self._dispatch_command(drone_id, "BASE", "Tiempo post-alerta completado. Regresando a base.")
                    del self.active_alerts[drone_id]

    def _check_external_commands(self):
        if not COMMANDS_FILE.exists():
            return
            
        try:
            with open(COMMANDS_FILE, "r", encoding="utf-8") as f:
                cmd = json.load(f)
                
            if cmd.get("action") == "GOTO":
                tx, tz = cmd.get("x"), cmd.get("z")
                
                # Encontrar el dron mas cercano
                closest_drone = None
                min_dist = float('inf')
                
                for did, state in self.drone_states.items():
                    pos = state.get("position", {})
                    dx = pos.get("x", 0) - tx
                    dz = pos.get("z", 0) - tz
                    dist = math.sqrt(dx**2 + dz**2)
                    if dist < min_dist:
                        min_dist = dist
                        closest_drone = did
                        
                if closest_drone:
                    out_cmd = {
                        "action": "GOTO",
                        "x": tx,
                        "z": tz,
                        "target_drone": closest_drone
                    }
                    self.emitter.send(json.dumps(out_cmd).encode("utf-8"))
                    print(f"[CC] Comando interactivo GOTO ({tx}, {tz}) asignado al Drone {closest_drone} (dist={min_dist:.1f}m)")
                    
            COMMANDS_FILE.unlink() # Borrar para no volver a leer
        except Exception:
            pass # Ignorar errores si el archivo se esta escribiendo


    # ─────────────────────────────────────────────────────────────────────────
    # REPORTES
    # ─────────────────────────────────────────────────────────────────────────

    def _save_alert_evidence(self, alert: dict):
        """Guarda la evidencia de una alerta en un archivo JSON."""
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:22]
        name = f"alerta_{alert['risk_level']}_drone{alert['drone_id']}_{ts}.json"
        path = REPORTS_DIR / name
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(alert, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[CC] Error guardando evidencia: {e}")

    def _generate_session_report(self):
        """Genera un reporte completo de la sesion de simulacion."""
        sim_time  = self.robot.getTime()
        report    = {
            "reporte"         : "Sesion de Vigilancia — Cienaga, Magdalena",
            "generado"        : datetime.now().isoformat(),
            "tiempo_simulacion_s": round(sim_time, 1),
            "duracion_real"   : str(datetime.now() - self.session_start),
            "total_mensajes"  : self.total_messages,
            "total_alertas"   : len(self.alert_log),
            "alertas_por_nivel": self._count_alerts_by_level(),
            "drones_activos"  : list(self.drone_states.keys()),
            "estado_drones"   : self._get_drone_summary(),
            "historial_alertas": self.alert_log[-50:],   # Ultimas 50 alertas
        }
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"reporte_sesion_{ts}.json"
        path = REPORTS_DIR / name
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"[CC] Reporte guardado: {name}")
        except Exception as e:
            print(f"[CC] Error generando reporte: {e}")
        return report

    def _count_alerts_by_level(self) -> dict:
        counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
        for a in self.alert_log:
            lvl = a.get("risk_level", "LOW")
            counts[lvl] = counts.get(lvl, 0) + 1
        return counts

    def _get_drone_summary(self) -> list:
        summary = []
        for did, state in self.drone_states.items():
            summary.append({
                "drone_id"   : did,
                "zone"       : state.get("zone", "?"),
                "state"      : state.get("state", "?"),
                "position"   : state.get("position", {}),
                "dist_total" : state.get("total_dist_m", 0),
                "alertas"    : state.get("alerts_sent", 0),
            })
        return summary

    def _write_shared_state(self):
        """Escribe el estado compartido para el dashboard en tiempo real."""
        state = {
            "timestamp"       : datetime.now().isoformat(),
            "sim_time"        : round(self.robot.getTime() if hasattr(self, 'robot') else 0, 1),
            "total_mensajes"  : self.total_messages,
            "total_alertas"   : len(self.alert_log),
            "alertas_por_nivel": self._count_alerts_by_level() if self.alert_log is not None else {},
            "drones"          : {},
            "ultimas_alertas" : self.alert_log[-10:] if self.alert_log else [],
        }
        for did, s in self.drone_states.items():
            state["drones"][str(did)] = {
                "id"      : did,
                "zone"    : s.get("zone", ""),
                "state"   : s.get("state", ""),
                "position": s.get("position", {}),
                "dist"    : s.get("total_dist_m", 0),
                "alertas" : s.get("alerts_sent", 0),
                "waypoint": s.get("waypoint", 0),
            }
        try:
            with open(SHARED_STATE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # BUCLE PRINCIPAL
    # ─────────────────────────────────────────────────────────────────────────

    def run(self):
        """Bucle principal del supervisor."""
        step = 0
        while self.robot.step(self.timestep) != -1:
            step += 1

            # Procesar mensajes entrantes
            self._process_incoming()

            sim_time = self.robot.getTime()

            # Manejar ciclo de vida de alertas activas
            self._manage_interventions(sim_time)

            # Revisar comandos enviados desde el dashboard
            self._check_external_commands()

            # Actualizar estado compartido cada 100 pasos
            if step % 100 == 0:
                self._write_shared_state()

            # Reporte periodico
            if sim_time - self.last_report_time >= self.report_interval:
                self.last_report_time = sim_time
                self._generate_session_report()
                counts = self._count_alerts_by_level()
                print(f"[CC] t={sim_time:.0f}s | Mensajes={self.total_messages} | "
                      f"Alertas: LOW={counts['LOW']} MED={counts['MEDIUM']} HIGH={counts['HIGH']}")

        # Reporte final al terminar simulacion
        print("\n[CC] Simulacion finalizada. Generando reporte final...")
        self._generate_session_report()
        self._write_shared_state()


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    cc = ControlCenter()
    cc.run()
