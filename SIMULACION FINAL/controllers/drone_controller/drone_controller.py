import sys
import os
import math
import json
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from controller import Supervisor

try:
    from ai.detector import ObjectDetector
    from ai.classifier import RiskClassifier
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("[WARN] Modulos AI no encontrados. Usando modo basico.")

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES DE VUELO (Kinematic)
# ─────────────────────────────────────────────────────────────────────────────
TARGET_ALTITUDE    = 15.0    # Altitud de patrullaje (m)
TAKEOFF_SPEED      = 3.0     # Velocidad de ascenso (m/s)
PATROL_SPEED       = 6.0     # Velocidad horizontal de patrullaje (m/s)
WAYPOINT_TOLERANCE = 3.0     # Radio para considerar waypoint alcanzado (m)

# ─────────────────────────────────────────────────────────────────────────────
# RUTAS DE PATRULLAJE POR ZONA
# ─────────────────────────────────────────────────────────────────────────────
PATROL_ROUTES = {
    "norte": [
        ( 15,  20), ( 30,  20), ( 50,  50), ( 60,  60),
        ( 20,  55), (-20,  50), (-30,  28), (-60,  40),
        (-70,  20), (-20,  20), (  0,   0),
    ],
    "sur": [
        ( 20, -20), ( 35, -20), ( 50, -20), ( 38, -35),
        ( 20, -35), (-20, -20), (-35, -20), (-55, -25),
        (-70, -70), (  0, -60), (  0,   0),
    ],
    "central": [
        (  0,   0), ( 20,   0), ( 40,   0), ( 70,  70),
        ( 40,  40), (  0,  40), (-40,   0), (-40, -40),
        (  0, -40), ( 40, -40), (  0,   0),
    ],
}

RISK_ZONES = [
    {"name": "Callejon_Suroeste", "center": (-70, -70), "radius": 10, "risk_multiplier": 2.0},
    {"name": "Periferia_Noreste",  "center": ( 70,  70), "radius":  8, "risk_multiplier": 1.8},
    {"name": "Bodega_Abandonada",  "center": (-70,  20), "radius":  7, "risk_multiplier": 2.5},
]


class DroneController:
    """Controlador de dron usando Supervisor.setVelocity para movimiento directo."""

    def __init__(self, drone_id: int, zone: str):
        self.drone_id  = drone_id
        self.zone      = zone
        self.robot     = Supervisor()
        self.timestep  = int(self.robot.getBasicTimeStep())

        # ── Nodo propio (para setVelocity) ───────────────────────────────────
        self.node = self.robot.getSelf()

        # ── Sensores ──────────────────────────────────────────────────────────
        self.gps = self.robot.getDevice("gps")
        self.gps.enable(self.timestep)

        self.camera = self.robot.getDevice("camera")
        self.camera.enable(self.timestep * 4)

        # ── Motores (solo animacion visual) ───────────────────────────────────
        self.fl_motor = self.robot.getDevice("front left propeller")
        self.fr_motor = self.robot.getDevice("front right propeller")
        self.rl_motor = self.robot.getDevice("rear left propeller")
        self.rr_motor = self.robot.getDevice("rear right propeller")

        for m in [self.fl_motor, self.fr_motor, self.rl_motor, self.rr_motor]:
            if m:
                m.setPosition(float('inf'))
                m.setVelocity(50.0)

        # Acomodar camara (opcional — solo disponible en Mavic2Pro oficial)
        try:
            n = self.robot.getNumberOfDevices()
            device_names = [self.robot.getDeviceByIndex(i).getName() for i in range(n)]
            if "camera pitch" in device_names:
                cam_pitch = self.robot.getDevice("camera pitch")
                cam_pitch.setPosition(0.7)
        except Exception:
            pass

        # ── Comunicacion ──────────────────────────────────────────────────────
        self.emitter  = self.robot.getDevice(f"emitter_d{drone_id}")
        self.receiver = self.robot.getDevice(f"receiver_d{drone_id}")
        if self.receiver:
            self.receiver.enable(self.timestep)

        # ── Estado ────────────────────────────────────────────────────────────
        self.state          = "TAKEOFF"
        self.waypoints      = list(PATROL_ROUTES.get(zone, PATROL_ROUTES["central"]))
        self.waypoint_index = 0
        self.total_distance = 0.0
        self.alerts_sent    = 0
        self.last_pos_xz    = None
        self.base_pos       = None
        
        self.patrol_start_time = 0.0
        self.patrol_duration_limit = 60.0
        self.landed_time = 0.0

        # ── IA ────────────────────────────────────────────────────────────────
        if AI_AVAILABLE:
            self.detector   = ObjectDetector(drone_id=drone_id)
            self.classifier = RiskClassifier()
        else:
            self.detector = self.classifier = None

        print(f"[Drone {self.drone_id}] ✓ Inicializado (Modo Kinematic) | "
              f"Zona: {self.zone} | {len(self.waypoints)} waypoints | Alt: {TARGET_ALTITUDE}m")

    # ─────────────────────────────────────────────────────────────────────────
    # POSICION ACTUAL
    # ─────────────────────────────────────────────────────────────────────────

    def _get_pos(self):
        v = self.gps.getValues()
        return v[0], v[1], v[2]

    # ─────────────────────────────────────────────────────────────────────────
    # MOVIMIENTO DIRECTO (Supervisor.setVelocity)
    # ─────────────────────────────────────────────────────────────────────────

    def _set_velocity(self, vx: float, vy: float, vz: float):
        self.node.setVelocity([vx, vy, vz, 0.0, 0.0, 0.0])

    # ─────────────────────────────────────────────────────────────────────────
    # MAQUINA DE ESTADOS
    # ─────────────────────────────────────────────────────────────────────────

    def step_takeoff(self) -> str:
        """Asciende verticalmente hasta TARGET_ALTITUDE."""
        x, y, z = self._get_pos()
        if not self.base_pos and not math.isnan(x):
            self.base_pos = (x, z)

        if y >= TARGET_ALTITUDE - 0.5:
            self._set_velocity(0, 0, 0)
            print(f"[Drone {self.drone_id}] ✈ Altitud {y:.1f}m alcanzada "
                  f"en t={self.robot.getTime():.1f}s — iniciando patrullaje")
            self.patrol_start_time = self.robot.getTime()
            return "PATROL"

        self._set_velocity(0, TAKEOFF_SPEED, 0)
        return "TAKEOFF"

    def step_patrol(self) -> str:
        """Navega entre waypoints a TARGET_ALTITUDE."""
        x, y, z = self._get_pos()

        diff = TARGET_ALTITUDE - y
        if abs(diff) > 1.0:
            vy = TAKEOFF_SPEED * (1.0 if diff > 0 else -0.5)
        else:
            vy = 0.0

        if not self.waypoints:
            self._set_velocity(0, vy, 0)
            return "HOVER"

        # Check cyclic patrol time limit
        if self.patrol_duration_limit != float('inf'):
            if self.robot.getTime() - self.patrol_start_time >= self.patrol_duration_limit:
                if len(self.waypoints) != 1 or self.waypoints[0] != self.base_pos:
                    print(f"[Drone {self.drone_id}] 60s de patrullaje completados. Regresando a base.")
                    if self.base_pos:
                        self.waypoints = [self.base_pos]
                        self.waypoint_index = 0

        wx, wz = self.waypoints[self.waypoint_index]
        dx = wx - x
        dz = wz - z
        dist = math.sqrt(dx**2 + dz**2)

        if self.last_pos_xz:
            lx, lz = self.last_pos_xz
            self.total_distance += math.sqrt((x - lx)**2 + (z - lz)**2)
        self.last_pos_xz = (x, z)

        if dist < WAYPOINT_TOLERANCE:
            if len(self.waypoints) == 1 and self.waypoints[0] == self.base_pos:
                print(f"[Drone {self.drone_id}] BASE ALCANZADA. Aterrizando...")
                return "LANDING"
            self.waypoint_index = (self.waypoint_index + 1) % len(self.waypoints)
            wx, wz = self.waypoints[self.waypoint_index]
            print(f"[Drone {self.drone_id}] → Waypoint {self.waypoint_index}: ({wx}, {wz})")
            dx = wx - x
            dz = wz - z
            dist = math.sqrt(dx**2 + dz**2) or 1.0

        speed = min(PATROL_SPEED, dist)
        vx = (dx / dist) * speed
        vz = (dz / dist) * speed

        # Aplicar inclinacion visual usando el torque del supervisor
        # Para inclinar hacia adelante en la direccion del movimiento:
        # Orientamos el dron usando rotacion manual?
        # Por ahora lo movemos como un ovni (traslacion pura) para maxima estabilidad
        self._set_velocity(vx, vy, vz)
        return "PATROL"

    def step_hover(self) -> str:
        _, y, _ = self._get_pos()
        if y < TARGET_ALTITUDE - 0.5:
            vy = 0.5
        elif y > TARGET_ALTITUDE + 0.5:
            vy = -0.3
        else:
            vy = 0.0
        self._set_velocity(0, vy, 0)
        return "HOVER"

    def step_landing(self) -> str:
        _, y, _ = self._get_pos()
        if y <= 0.5:
            self._set_velocity(0, 0, 0)
            self.landed_time = self.robot.getTime()
            return "LANDED"
        self._set_velocity(0, -TAKEOFF_SPEED, 0)
        return "LANDING"

    def step_landed(self) -> str:
        self._set_velocity(0, 0, 0)
        # Esperar 5 segundos en base antes de iniciar la siguiente ronda de 60s
        if self.robot.getTime() - self.landed_time >= 5.0:
            print(f"[Drone {self.drone_id}] Iniciando nueva ronda de patrullaje ciclico (60s).")
            self.waypoints = list(PATROL_ROUTES.get(self.zone, PATROL_ROUTES["central"]))
            self.waypoint_index = 0
            self.patrol_duration_limit = 60.0
            return "TAKEOFF"
        return "LANDED"

    # ─────────────────────────────────────────────────────────────────────────
    # DETECCION Y ALERTAS
    # ─────────────────────────────────────────────────────────────────────────

    def _is_in_risk_zone(self, x, z):
        for zone in RISK_ZONES:
            cx, cz = zone["center"]
            if math.sqrt((x - cx)**2 + (z - cz)**2) <= zone["radius"]:
                return zone
        return None

    def _run_detection(self):
        if not AI_AVAILABLE or not self.detector:
            return None
        x, alt, z = self._get_pos()
        risk_zone = self._is_in_risk_zone(x, z)
        risk_mult = risk_zone["risk_multiplier"] if risk_zone else 1.0
        try:
            img = self.camera.getImage()
            dets = self.detector.detect(
                image=img, position=(x, alt, z), risk_mult=risk_mult,
                width=self.camera.getWidth(), height=self.camera.getHeight(),
                simulation_time=self.robot.getTime()
            )
            if not dets:
                return None
            return self.classifier.classify(
                detections=dets, position=(x, alt, z),
                drone_id=self.drone_id, simulation_time=self.robot.getTime(),
                risk_zone=risk_zone,
            )
        except Exception:
            return None

    def _send_status(self, alert=None):
        if not self.emitter:
            return
        x, alt, z = self._get_pos()
        payload = {
            "type"         : "STATUS",
            "drone_id"     : self.drone_id,
            "zone"         : self.zone,
            "position"     : {"x": round(x, 2), "y": round(alt, 2), "z": round(z, 2)},
            "waypoint"     : self.waypoint_index,
            "state"        : self.state,
            "altitude"     : round(alt, 2),
            "total_dist_m" : round(self.total_distance, 1),
            "alerts_sent"  : self.alerts_sent,
            "sim_time"     : round(self.robot.getTime(), 1),
        }
        if alert:
            payload["type"]  = "ALERT"
            payload["alert"] = alert
            self.alerts_sent += 1
        try:
            self.emitter.send(json.dumps(payload).encode("utf-8"))
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # BUCLE PRINCIPAL
    # ─────────────────────────────────────────────────────────────────────────

    def run(self):
        step_counter = 0

        while self.robot.step(self.timestep) != -1:
            step_counter += 1

            if   self.state == "TAKEOFF": self.state = self.step_takeoff()
            elif self.state == "PATROL":  self.state = self.step_patrol()
            elif self.state == "HOVER":   self.state = self.step_hover()
            elif self.state == "LANDING": self.state = self.step_landing()
            elif self.state == "LANDED":  self.state = self.step_landed()

            if step_counter % 40 == 0 and self.state == "PATROL":
                result = self._run_detection()
                if result and result.get("risk_level") in ("LOW", "MEDIUM", "HIGH"):
                    x, alt, z = self._get_pos()
                    print(f"[Drone {self.drone_id}] ⚠ ALERTA {result['risk_level']}: "
                          f"{result['description']} @ ({x:.1f}, {z:.1f})")
                    self._send_status(alert=result)

            if step_counter % 50 == 0:
                self._send_status()

            if self.receiver and self.receiver.getQueueLength() > 0:
                try:
                    raw = self.receiver.getString()
                    cmd = json.loads(raw)
                    self._handle_command(cmd)
                    self.receiver.nextPacket()
                except Exception:
                    pass

    def _handle_command(self, cmd: dict):
        target = cmd.get("target_drone")
        if target and target != self.drone_id:
            return

        action = cmd.get("action", "")
        if action == "HOVER":
            self.state = "HOVER"
            print(f"[Drone {self.drone_id}] Comando HOVER recibido")
        elif action == "RESUME":
            self.state = "PATROL"
            self.patrol_duration_limit = float('inf') # El CC manejara el regreso a base
            print(f"[Drone {self.drone_id}] Resumiendo patrullaje (controlado por CC)")
        elif action == "BASE":
            self.state = "PATROL"
            if self.base_pos:
                self.waypoints = [self.base_pos]
                self.waypoint_index = 0
            print(f"[Drone {self.drone_id}] Comando BASE recibido. Regresando.")
        elif action == "GOTO":
            wx = cmd.get("x", 0)
            wz = cmd.get("z", 0)
            self.waypoints.insert(self.waypoint_index, (wx, wz))

# ─────────────────────────────────────────────────────────────────────────────
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id",   type=int, default=1)
    parser.add_argument("--zone", type=str, default="central")
    args, _ = parser.parse_known_args()
    return args

if __name__ == "__main__":
    args = parse_args()
    DroneController(drone_id=args.id, zone=args.zone).run()
