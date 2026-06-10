"""
==============================================================================
DASHBOARD DE MONITOREO EN TIEMPO REAL
Sistema de Vigilancia con Drones — Cienaga, Magdalena
==============================================================================
Archivo    : dashboard.py
Descripcion: Interfaz grafica de monitoreo en tiempo real.
             Muestra mapa 2D del area con posiciones de drones,
             panel de alertas con color por nivel de riesgo,
             estadisticas en vivo y registro de eventos.

Requisitos : Python 3.8+ | tkinter (incluido en Python) | No requiere extras
Ejecucion  : python monitor/dashboard.py
             (ejecutar JUNTO a la simulacion Webots, en otra terminal)
==============================================================================
"""

import tkinter as tk
from tkinter import ttk, font
import json
import math
import time
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACION
# ─────────────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SHARED_STATE = PROJECT_ROOT / "reports" / "shared_state.json"
REFRESH_MS   = 500       # Refresco del dashboard cada 500ms

# Mapa: coordenadas del mundo → pixeles del canvas
WORLD_MIN    = -180      # metros
WORLD_MAX    =  180
CANVAS_SIZE  =  500      # pixeles

# Colores del tema
BG_DARK      = "#0d1117"
BG_PANEL     = "#161b22"
BG_CARD      = "#1f2937"
ACCENT_BLUE  = "#2d7dd2"
ACCENT_CYAN  = "#00d4ff"
COLOR_LOW    = "#27ae60"
COLOR_MEDIUM = "#f39c12"
COLOR_HIGH   = "#e74c3c"
COLOR_WHITE  = "#e6edf3"
COLOR_GRAY   = "#8b949e"
COLOR_GRID   = "#21262d"

# Colores de drones
DRONE_COLORS = {1: "#00d4ff", 2: "#ff6b35", 3: "#a855f7"}
DRONE_NAMES  = {1: "Drone-1 Norte", 2: "Drone-2 Sur", 3: "Drone-3 Central"}


def world_to_canvas(x: float, z: float) -> tuple:
    """Convierte coordenadas del mundo a pixeles del canvas."""
    px = int((x - WORLD_MIN) / (WORLD_MAX - WORLD_MIN) * CANVAS_SIZE)
    py = int((z - WORLD_MIN) / (WORLD_MAX - WORLD_MIN) * CANVAS_SIZE)
    py = CANVAS_SIZE - py   # Invertir eje Y
    return px, py

def canvas_to_world(px: int, py: int) -> tuple:
    """Convierte pixeles del canvas a coordenadas del mundo."""
    py = CANVAS_SIZE - py   # Des-invertir eje Y
    x = (px / CANVAS_SIZE) * (WORLD_MAX - WORLD_MIN) + WORLD_MIN
    z = (py / CANVAS_SIZE) * (WORLD_MAX - WORLD_MIN) + WORLD_MIN
    return x, z


# ─────────────────────────────────────────────────────────────────────────────
class DroneMonitorDashboard:
    """Dashboard de monitoreo de drones en tiempo real."""

    def __init__(self, root: tk.Tk):
        self.root      = root
        self.root.title("Centro de Monitoreo — Drones Ciénaga, Magdalena")
        self.root.configure(bg=BG_DARK)
        self.root.geometry("1400x820")
        self.root.minsize(1100, 700)

        self._setup_fonts()
        self._build_ui()

        # Estado
        self.drone_trails    = {1: [], 2: [], 3: []}   # Historial de posiciones
        self.alert_count     = 0
        self.last_sim_time   = 0.0
        self.start_wall_time = time.time()

        # Iniciar bucle de refresco
        self.root.after(REFRESH_MS, self._refresh)

    # ─────────────────────────────────────────────────────────────────────────
    def _on_map_click(self, event):
        """Manejador de clics en el mapa para enviar comandos a los drones."""
        wx, wz = canvas_to_world(event.x, event.y)
        cmd_path = PROJECT_ROOT / "reports" / "commands.json"
        
        cmd = {
            "action": "GOTO",
            "x": round(wx, 2),
            "z": round(wz, 2),
            "timestamp": time.time()
        }
        
        try:
            with open(cmd_path, "w", encoding="utf-8") as f:
                json.dump(cmd, f)
            print(f"Comando GOTO enviado a ({wx:.1f}, {wz:.1f})")
            
            # Dibujar un marcador temporal en el canvas
            r = 5
            self.canvas.create_oval(event.x-r, event.y-r, event.x+r, event.y+r,
                                    outline=COLOR_HIGH, width=2, tags="target_marker")
            self.root.after(2000, lambda: self.canvas.delete("target_marker"))
        except Exception as e:
            print(f"Error escribiendo comando: {e}")

    def _setup_fonts(self):
        self.font_title   = font.Font(family="Segoe UI", size=14, weight="bold")
        self.font_header  = font.Font(family="Segoe UI", size=11, weight="bold")
        self.font_body    = font.Font(family="Segoe UI", size=10)
        self.font_small   = font.Font(family="Segoe UI", size=9)
        self.font_mono    = font.Font(family="Consolas", size=9)
        self.font_big     = font.Font(family="Segoe UI", size=22, weight="bold")

    # ─────────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        """Construye toda la interfaz grafica."""

        # ── Barra de titulo ──────────────────────────────────────────────────
        title_bar = tk.Frame(self.root, bg="#0a0f1a", height=56)
        title_bar.pack(fill=tk.X, side=tk.TOP)
        title_bar.pack_propagate(False)

        tk.Label(title_bar, text="🛸  CENTRO DE MONITOREO — DRONES CIÉNAGA",
                 font=self.font_title, fg=ACCENT_CYAN, bg="#0a0f1a",
                 padx=20).pack(side=tk.LEFT, pady=12)

        self.lbl_clock = tk.Label(title_bar, text="",
                                   font=self.font_body, fg=COLOR_GRAY, bg="#0a0f1a")
        self.lbl_clock.pack(side=tk.RIGHT, padx=20, pady=12)

        self.lbl_status_dot = tk.Label(title_bar, text="● EN VIVO",
                                        font=self.font_small, fg=COLOR_LOW, bg="#0a0f1a")
        self.lbl_status_dot.pack(side=tk.RIGHT, padx=10)

        # ── Contenedor principal ──────────────────────────────────────────────
        main = tk.Frame(self.root, bg=BG_DARK)
        main.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        # ── Columna izquierda: mapa ───────────────────────────────────────────
        left = tk.Frame(main, bg=BG_DARK)
        left.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 6))

        map_card = tk.Frame(left, bg=BG_PANEL, relief=tk.FLAT,
                             highlightbackground=ACCENT_BLUE, highlightthickness=1)
        map_card.pack(fill=tk.BOTH)

        tk.Label(map_card, text="🗺  MAPA DE PATRULLAJE — Ciénaga, Magdalena",
                 font=self.font_header, fg=ACCENT_CYAN, bg=BG_PANEL,
                 pady=8, padx=10, anchor=tk.W).pack(fill=tk.X)

        self.canvas = tk.Canvas(map_card, width=CANVAS_SIZE, height=CANVAS_SIZE,
                                 bg="#0d1a2e", highlightthickness=0)
        self.canvas.pack(padx=8, pady=(0, 8))
        self.canvas.bind("<Button-1>", self._on_map_click)

        self._draw_map_static()

        # Leyenda del mapa
        legend = tk.Frame(map_card, bg=BG_PANEL)
        legend.pack(fill=tk.X, padx=10, pady=(0, 8))

        # Fila 1: drones
        row1 = tk.Frame(legend, bg=BG_PANEL)
        row1.pack(fill=tk.X)
        for did, color in DRONE_COLORS.items():
            tk.Label(row1, text=f"● {DRONE_NAMES[did]}",
                     fg=color, bg=BG_PANEL, font=self.font_small).pack(side=tk.LEFT, padx=6)
        tk.Label(row1, text="-- Ruta patrullaje",
                 fg=COLOR_GRAY, bg=BG_PANEL, font=self.font_small).pack(side=tk.LEFT, padx=6)

        # Fila 2: zonas
        row2 = tk.Frame(legend, bg=BG_PANEL)
        row2.pack(fill=tk.X)
        tk.Label(row2, text="🔴 Zona riesgo", fg=COLOR_HIGH,
                 bg=BG_PANEL, font=self.font_small).pack(side=tk.LEFT, padx=6)
        tk.Label(row2, text="🟢 Zona verde", fg="#27ae60",
                 bg=BG_PANEL, font=self.font_small).pack(side=tk.LEFT, padx=6)
        tk.Label(row2, text="🏢 Edificios", fg="#ccddee",
                 bg=BG_PANEL, font=self.font_small).pack(side=tk.LEFT, padx=6)
        tk.Label(row2, text="🖱 Clic → enviar dron", fg=ACCENT_CYAN,
                 bg=BG_PANEL, font=self.font_small).pack(side=tk.RIGHT, padx=6)


        # ── Columna derecha ────────────────────────────────────────────────────
        right = tk.Frame(main, bg=BG_DARK)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # ── Tarjetas de KPIs ────────────────────────────────────────────────
        kpi_row = tk.Frame(right, bg=BG_DARK)
        kpi_row.pack(fill=tk.X, pady=(0, 6))

        self.kpi_vars = {}
        kpi_defs = [
            ("total_alertas",    "🚨 Alertas Total",   COLOR_HIGH),
            ("alertas_high",     "🔴 Nivel Alto",       COLOR_HIGH),
            ("alertas_medium",   "🟡 Nivel Medio",      COLOR_MEDIUM),
            ("alertas_low",      "🟢 Nivel Bajo",       COLOR_LOW),
            ("sim_time",         "⏱ Tiempo Sim.",      ACCENT_CYAN),
        ]
        for key, label, color in kpi_defs:
            card = tk.Frame(kpi_row, bg=BG_CARD, padx=12, pady=8,
                            relief=tk.FLAT,
                            highlightbackground=color, highlightthickness=1)
            card.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
            var = tk.StringVar(value="0")
            tk.Label(card, textvariable=var, font=self.font_big,
                     fg=color, bg=BG_CARD).pack()
            tk.Label(card, text=label, font=self.font_small,
                     fg=COLOR_GRAY, bg=BG_CARD).pack()
            self.kpi_vars[key] = var

        # ── Estado de drones ────────────────────────────────────────────────
        drones_card = tk.Frame(right, bg=BG_PANEL,
                                highlightbackground=ACCENT_BLUE, highlightthickness=1)
        drones_card.pack(fill=tk.X, pady=(0, 6))

        tk.Label(drones_card, text="📡  ESTADO DE DRONES",
                 font=self.font_header, fg=ACCENT_CYAN, bg=BG_PANEL,
                 pady=6, padx=10, anchor=tk.W).pack(fill=tk.X)

        self.drone_labels = {}
        for did in [1, 2, 3]:
            row = tk.Frame(drones_card, bg=BG_PANEL)
            row.pack(fill=tk.X, padx=10, pady=2)

            color = DRONE_COLORS[did]
            tk.Label(row, text=f"● {DRONE_NAMES[did]:20s}",
                     fg=color, bg=BG_PANEL, font=self.font_body,
                     width=22, anchor=tk.W).pack(side=tk.LEFT)

            lbl = tk.Label(row, text="Esperando conexion...",
                           fg=COLOR_GRAY, bg=BG_PANEL, font=self.font_mono,
                           anchor=tk.W)
            lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.drone_labels[did] = lbl

        # Padding
        tk.Frame(drones_card, bg=BG_PANEL, height=6).pack()

        # ── Panel de alertas ────────────────────────────────────────────────
        alerts_card = tk.Frame(right, bg=BG_PANEL,
                                highlightbackground=COLOR_HIGH, highlightthickness=1)
        alerts_card.pack(fill=tk.BOTH, expand=True)

        header_row = tk.Frame(alerts_card, bg=BG_PANEL)
        header_row.pack(fill=tk.X, padx=10, pady=(6, 0))

        tk.Label(header_row, text="🚨  REGISTRO DE ALERTAS",
                 font=self.font_header, fg=ACCENT_CYAN, bg=BG_PANEL).pack(side=tk.LEFT)

        self.lbl_alert_count = tk.Label(header_row, text="0 alertas",
                                         font=self.font_small, fg=COLOR_GRAY, bg=BG_PANEL)
        self.lbl_alert_count.pack(side=tk.RIGHT)

        # Cabecera de tabla
        cols = tk.Frame(alerts_card, bg="#1a2332")
        cols.pack(fill=tk.X, padx=10, pady=2)
        headers = [("HORA",15), ("DRONE",8), ("NIVEL",8), ("DESCRIPCION",50), ("POS (X,Z)",14)]
        for text, w in headers:
            tk.Label(cols, text=text, font=self.font_small, fg=COLOR_GRAY,
                     bg="#1a2332", width=w, anchor=tk.W).pack(side=tk.LEFT)

        # Frame scrollable de alertas
        self.alerts_frame_outer = tk.Frame(alerts_card, bg=BG_PANEL)
        self.alerts_frame_outer.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))

        self.alerts_canvas = tk.Canvas(self.alerts_frame_outer, bg=BG_PANEL,
                                        highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.alerts_frame_outer, orient=tk.VERTICAL,
                                   command=self.alerts_canvas.yview)
        self.alerts_inner = tk.Frame(self.alerts_canvas, bg=BG_PANEL)
        self.alerts_inner.bind("<Configure>",
                                lambda e: self.alerts_canvas.configure(
                                    scrollregion=self.alerts_canvas.bbox("all")
                                ))
        self.alerts_canvas.create_window((0, 0), window=self.alerts_inner, anchor=tk.NW)
        self.alerts_canvas.configure(yscrollcommand=scrollbar.set)
        self.alerts_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.displayed_alerts = set()

    # ─────────────────────────────────────────────────────────────────────────
    def _draw_map_static(self):
        """Dibuja los elementos estaticos del mapa reflejando el mundo 3D (SimplePoly City)."""
        c = self.canvas

        # ── Fondo base (suelo) ─────────────────────────────────────────────────
        c.create_rectangle(0, 0, CANVAS_SIZE, CANVAS_SIZE,
                           fill="#111a11", outline="")

        # ── Grid suave ─────────────────────────────────────────────────────────
        for i in range(0, CANVAS_SIZE + 1, 25):
            c.create_line(i, 0, i, CANVAS_SIZE, fill="#1a2a1a", width=1)
            c.create_line(0, i, CANVAS_SIZE, i, fill="#1a2a1a", width=1)

        # ── Calles principales (ancho 8m → ~20px) ──────────────────────────────
        cx, cy = world_to_canvas(0, 0)
        # Horizontal central
        c.create_rectangle(0, cy-10, CANVAS_SIZE, cy+10,
                           fill="#252525", outline="")
        c.create_line(0, cy, CANVAS_SIZE, cy, fill="#3a3a3a", width=1, dash=(6,4))
        # Vertical central
        c.create_rectangle(cx-10, 0, cx+10, CANVAS_SIZE,
                           fill="#252525", outline="")
        c.create_line(cx, 0, cx, CANVAS_SIZE, fill="#3a3a3a", width=1, dash=(6,4))

        # Calles secundarias (ancho 5m → ~12px)
        for wz in [40, -40]:
            _, py = world_to_canvas(0, wz)
            c.create_rectangle(0, py-6, CANVAS_SIZE, py+6,
                               fill="#202020", outline="")
        for wx in [40, -40]:
            px, _ = world_to_canvas(wx, 0)
            c.create_rectangle(px-6, 0, px+6, CANVAS_SIZE,
                               fill="#202020", outline="")

        # ── Zonas de riesgo (debajo de edificios) ─────────────────────────────
        risk_zones = [
            (-70, -70, 12, "Callejón\nSuroeste"),
            ( 70,  70,  9, "Periferia\nNoreste"),
            (-70,  20,  7, "Bodega\nAbandona"),
        ]
        for rx, rz, rr, rlbl in risk_zones:
            px, py = world_to_canvas(rx, rz)
            r = int(rr * CANVAS_SIZE / (WORLD_MAX - WORLD_MIN))
            c.create_oval(px-r*2, py-r*2, px+r*2, py+r*2,
                          outline=COLOR_HIGH, fill="#2a0000",
                          stipple="gray25", width=2)
            c.create_text(px, py, text=rlbl, fill=COLOR_HIGH,
                          font=("Segoe UI", 6, "bold"), justify="center")


        # ── Parque central ─────────────────────────────────────────────────────
        px, py = world_to_canvas(0, 0)
        c.create_rectangle(px-15, py-15, px+15, py+15,
                           fill="#0a2a0a", outline="#27ae60", width=1)
        c.create_text(px, py, text="⬛\nParque", fill="#27ae60",
                      font=("Segoe UI", 6), justify="center")

        # Parque noroeste
        px2, py2 = world_to_canvas(-60, 40)
        c.create_rectangle(px2-18, py2-18, px2+18, py2+18,
                           fill="#0d2a0d", outline="#27ae60", width=1)
        c.create_text(px2, py2, text="Zona\nVerde", fill="#27ae60",
                      font=("Segoe UI", 6), justify="center")

        # ── Edificios ──────────────────────────────────────────────────────────
        # Formato: (cx_mundo, cz_mundo, ancho_px, alto_px, color_fill, etiqueta)
        buildings = [
            # ZONA NORTE — Residencial
            ( 20,  20, 12, 12, "#1e3a2a", "Viv."),
            ( 30,  25, 10, 10, "#1e352a", "Viv."),
            ( 20,  35, 12, 10, "#263a2a", "Viv."),
            ( 32,  15, 10, 12, "#1e3a26", "Viv."),
            ( 25,  50, 12, 12, "#1e3020", "Viv."),
            ( 15,  55, 10, 10, "#243a2a", "Viv."),
            (-20,  20, 12, 12, "#1e3a2a", "Viv."),
            (-30,  28, 10, 10, "#1e352a", "Viv."),
            (-22,  50, 12, 10, "#263a2a", "Viv."),

            # ZONA NORTE — Colegio / Complejo educativo
            ( 55,  55, 34, 20, "#1a3a1a", "🏫 Colegio"),
            ( 55,  42, 20, 12, "#183518", "Dep. Colegio"),

            # ZONA SUR — Comercial
            ( 20, -20, 20, 14, "#1a2840", "🏢 Comercial 1"),
            ( 35, -20, 15, 14, "#182438", "Comercial 2"),
            ( 50, -20, 24, 18, "#122030", "🏪 Supermercado"),
            ( 20, -35, 18, 12, "#1a203a", "Comercial 3"),
            ( 38, -35, 15, 12, "#181e38", "Comercial 4"),
            (-20, -20, 18, 12, "#2a1818", "Comercial 5"),
            (-35, -20, 15, 14, "#281616", "Comercial 6"),

            # ZONA OESTE — Policia + Bodega
            (-55, -25, 30, 20, "#14143a", "🚔 Policía"),
            (-70,  20, 18, 12, "#2a1414", "🏚 Bodega"),

            # Centro de control (sur)
            (  0, -60, 24, 18, "#0f2040", "🖥 C. Control"),
        ]

        for bx, bz, bw, bh, clr, lbl in buildings:
            px, py = world_to_canvas(bx, bz)
            x1, y1 = px - bw//2, py - bh//2
            x2, y2 = px + bw//2, py + bh//2
            # Sombra
            c.create_rectangle(x1+2, y1+2, x2+2, y2+2,
                               fill="#000000", outline="")
            # Edificio
            c.create_rectangle(x1, y1, x2, y2,
                               fill=clr, outline="#445566", width=1)
            # Etiqueta
            font_sz = 6 if len(lbl) > 8 else 7
            c.create_text(px, py, text=lbl, fill="#ccddee",
                          font=("Segoe UI", font_sz), justify="center")

        # ── Rutas de patrullaje por dron ───────────────────────────────────────
        patrol_routes = {
            1: [(-5, -5), ( 15,  20), ( 30,  20), ( 50,  50), ( 60,  60),
                ( 20,  55), (-20,  50), (-30,  28), (-60,  40), (-70,  20),
                (-20,  20), (  0,   0)],
            2: [(  5, -5), ( 20, -20), ( 35, -20), ( 50, -20), ( 38, -35),
                ( 20, -35), (-20, -20), (-35, -20), (-55, -25),
                (-70, -70), (  0, -60), (  0,   0)],
            3: [(  0,   5), (  0,   0), ( 20,   0), ( 40,   0), ( 70,  70),
                ( 40,  40), (  0,  40), (-40,   0), (-40, -40),
                (  0, -40), ( 40, -40), (  0,   0)],
        }
        route_colors = {1: "#00d4ff", 2: "#ff6b35", 3: "#a855f7"}
        for did, route in patrol_routes.items():
            pts = [world_to_canvas(wx, wz) for wx, wz in route]
            color = route_colors[did]
            for i in range(len(pts) - 1):
                c.create_line(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1],
                             fill=color, width=1, dash=(3, 5))
            # Waypoints
            for px2, py2 in pts:
                c.create_oval(px2-2, py2-2, px2+2, py2+2,
                             fill=DRONE_COLORS[did], outline="")

        # ── Etiquetas de zonas ─────────────────────────────────────────────────
        zone_labels = [
            (  45,  75, "ZONA NORTE\n(Residencial)", "#27ae60"),
            (  35, -55, "ZONA SUR\n(Comercial)",    "#2d7dd2"),
            ( -70,  -5, "ZONA OESTE\n(Industrial)", "#e67e22"),
            (  75, -30, "ZONA ESTE",                "#8b949e"),
        ]
        for zx, zz, ztxt, zclr in zone_labels:
            px2, py2 = world_to_canvas(zx, zz)
            c.create_text(px2, py2, text=ztxt, fill=zclr,
                          font=("Segoe UI", 6, "italic"), justify="center")

        # ── Escala ─────────────────────────────────────────────────────────────
        # 25px = 10m en escala 200m/500px
        scale_px = int(25 * CANVAS_SIZE / (WORLD_MAX - WORLD_MIN))
        c.create_line(10, CANVAS_SIZE - 14, 10 + scale_px, CANVAS_SIZE - 14,
                      fill=COLOR_WHITE, width=2)
        c.create_line(10, CANVAS_SIZE-10, 10, CANVAS_SIZE-18, fill=COLOR_WHITE, width=2)
        c.create_line(10+scale_px, CANVAS_SIZE-10, 10+scale_px,
                      CANVAS_SIZE-18, fill=COLOR_WHITE, width=2)
        c.create_text(10 + scale_px//2, CANVAS_SIZE - 7, text="25m",
                      fill=COLOR_GRAY, font=("Segoe UI", 7))

        # ── Norte ──────────────────────────────────────────────────────────────
        c.create_text(CANVAS_SIZE - 16, 16, text="N↑",
                      fill=ACCENT_CYAN, font=("Segoe UI", 10, "bold"))

        # ── Coordenadas de referencia ──────────────────────────────────────────
        for coord, label in [(-100, "−100"), (-50, "−50"), (0, "0"), (50, "50"), (100, "100")]:
            px2, _ = world_to_canvas(coord, 0)
            c.create_text(px2, CANVAS_SIZE - 3, text=label,
                          fill="#334433", font=("Segoe UI", 6))
            _, py2 = world_to_canvas(0, coord)
            c.create_text(3, py2, text=label,
                          fill="#334433", font=("Segoe UI", 6))



    # ─────────────────────────────────────────────────────────────────────────
    def _update_map_dynamic(self, state: dict):
        """Actualiza posiciones de drones en el mapa."""
        # Borrar trails y drones anteriores
        self.canvas.delete("drone")
        self.canvas.delete("trail")

        drones = state.get("drones", {})
        for did_str, data in drones.items():
            did  = int(did_str)
            pos  = data.get("position", {})
            x    = pos.get("x", 0)
            z    = pos.get("z", 0)
            color = DRONE_COLORS.get(did, "#ffffff")

            # Actualizar trail
            trail = self.drone_trails.get(did, [])
            trail.append((x, z))
            if len(trail) > 60:
                trail = trail[-60:]
            self.drone_trails[did] = trail

            # Dibujar trail
            if len(trail) > 1:
                for i in range(1, len(trail)):
                    x1c, y1c = world_to_canvas(*trail[i-1])
                    x2c, y2c = world_to_canvas(*trail[i])
                    alpha = int(200 * i / len(trail))
                    self.canvas.create_line(x1c, y1c, x2c, y2c,
                                            fill=color, width=1,
                                            tags="trail")

            # Dibujar dron
            px, py = world_to_canvas(x, z)
            r = 8
            self.canvas.create_oval(px-r, py-r, px+r, py+r,
                                    fill=color, outline="white", width=2,
                                    tags="drone")
            self.canvas.create_text(px, py-14, text=f"D{did}",
                                    fill=color, font=("Segoe UI", 8, "bold"),
                                    tags="drone")

    # ─────────────────────────────────────────────────────────────────────────
    def _update_drone_labels(self, state: dict):
        """Actualiza las etiquetas de estado de cada dron."""
        drones = state.get("drones", {})
        for did_str, data in drones.items():
            did   = int(did_str)
            pos   = data.get("position", {})
            x     = pos.get("x", 0)
            z     = pos.get("z", 0)
            alt   = pos.get("y", 0)
            dist  = data.get("dist", 0)
            st    = data.get("state", "?")
            wp    = data.get("waypoint", 0)
            alts  = data.get("alertas", 0)

            text = (f"Estado={st:8s} | Pos=({x:+6.1f},{z:+6.1f}) | "
                    f"Alt={alt:.1f}m | WP={wp} | Dist={dist:.0f}m | Alertas={alts}")

            if did in self.drone_labels:
                self.drone_labels[did].config(text=text, fg=COLOR_WHITE)

    # ─────────────────────────────────────────────────────────────────────────
    def _update_alerts(self, state: dict):
        """Agrega nuevas alertas al panel."""
        alerts = state.get("ultimas_alertas", [])
        for alert in alerts:
            # Identificador unico de la alerta
            uid = f"{alert.get('drone_id')}_{alert.get('sim_time')}"
            if uid in self.displayed_alerts:
                continue
            self.displayed_alerts.add(uid)

            risk      = alert.get("risk_level", "LOW")
            pos       = alert.get("position", {})
            desc      = alert.get("description", "")[:50]
            ts        = alert.get("timestamp", "")[:19].replace("T", " ")
            drone_id  = alert.get("drone_id", 0)

            color_map = {"LOW": COLOR_LOW, "MEDIUM": COLOR_MEDIUM, "HIGH": COLOR_HIGH}
            color     = color_map.get(risk, COLOR_WHITE)

            bg_color  = {"LOW": "#0d2a0d", "MEDIUM": "#2a1a00", "HIGH": "#2a0000"}.get(risk, BG_CARD)

            row = tk.Frame(self.alerts_inner, bg=bg_color, pady=3)
            row.pack(fill=tk.X, pady=1)

            tk.Label(row, text=ts[-8:], font=self.font_mono,
                     fg=COLOR_GRAY, bg=bg_color, width=8, anchor=tk.W).pack(side=tk.LEFT)
            tk.Label(row, text=f"D{drone_id}", font=self.font_mono,
                     fg=DRONE_COLORS.get(drone_id, COLOR_WHITE), bg=bg_color,
                     width=4).pack(side=tk.LEFT)
            tk.Label(row, text=f"[{risk:6s}]", font=self.font_mono,
                     fg=color, bg=bg_color, width=9).pack(side=tk.LEFT)
            tk.Label(row, text=desc, font=self.font_small,
                     fg=COLOR_WHITE, bg=bg_color, anchor=tk.W).pack(side=tk.LEFT, fill=tk.X, expand=True)
            tk.Label(row, text=f"({pos.get('x',0):.0f},{pos.get('z',0):.0f})",
                     font=self.font_mono, fg=COLOR_GRAY, bg=bg_color, width=12).pack(side=tk.RIGHT)

            self.alert_count += 1

        # Auto-scroll
        self.alerts_canvas.update_idletasks()
        self.alerts_canvas.yview_moveto(1.0)

    # ─────────────────────────────────────────────────────────────────────────
    def _update_kpis(self, state: dict):
        """Actualiza los KPI cards."""
        por_nivel = state.get("alertas_por_nivel", {})
        total     = state.get("total_alertas", 0)
        sim_time  = state.get("sim_time", 0)

        self.kpi_vars["total_alertas"].set(str(total))
        self.kpi_vars["alertas_high"].set(str(por_nivel.get("HIGH", 0)))
        self.kpi_vars["alertas_medium"].set(str(por_nivel.get("MEDIUM", 0)))
        self.kpi_vars["alertas_low"].set(str(por_nivel.get("LOW", 0)))
        self.kpi_vars["sim_time"].set(f"{sim_time:.0f}s")
        self.lbl_alert_count.config(text=f"{total} alertas registradas")

    # ─────────────────────────────────────────────────────────────────────────
    def _refresh(self):
        """Bucle de refresco principal del dashboard."""
        # Actualizar reloj
        now = datetime.now().strftime("%d/%m/%Y  %H:%M:%S")
        self.lbl_clock.config(text=now)

        # Parpadeo del indicador EN VIVO
        current_color = self.lbl_status_dot.cget("fg")
        new_color     = COLOR_LOW if current_color == COLOR_GRAY else COLOR_GRAY
        self.lbl_status_dot.config(fg=new_color)

        # Leer estado compartido
        state = self._load_shared_state()
        if state:
            self._update_map_dynamic(state)
            self._update_drone_labels(state)
            self._update_alerts(state)
            self._update_kpis(state)

        self.root.after(REFRESH_MS, self._refresh)

    def _load_shared_state(self) -> Optional[dict]:
        """Lee el archivo de estado compartido generado por el control center."""
        if not SHARED_STATE.exists():
            return None
        try:
            with open(SHARED_STATE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None


# ─────────────────────────────────────────────────────────────────────────────
# PUNTO DE ENTRADA
# ─────────────────────────────────────────────────────────────────────────────
def main():
    root = tk.Tk()
    root.resizable(True, True)

    # Icono (si existe)
    try:
        root.iconbitmap(default="")
    except Exception:
        pass

    app = DroneMonitorDashboard(root)

    # Mensaje de bienvenida
    print("=" * 60)
    print("  Dashboard de Monitoreo — Ciénaga Drone System")
    print(f"  Estado: {SHARED_STATE}")
    print("  Inicia Webots para ver datos en vivo.")
    print("=" * 60)

    root.mainloop()


if __name__ == "__main__":
    main()
