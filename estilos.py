"""
================================================================================
 BrachioDiag - Módulo Centralizado de Estilos, Colores, Fuentes y Breakpoints
 Desarrolladora: Angélica Serracín
 Materia: Sistemas Operativos | UTP - Centro Regional de Chiriquí
================================================================================
"""

import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont


# ==============================================================================
# RESOLUCIÓN SEGURA DE RUTAS (DESARROLLO Y PYINSTALLER)
# ==============================================================================

def ruta_recurso(ruta_relativa: str) -> Path:
    """
    Calcula la ruta absoluta hacia un recurso dentro del proyecto.
    Compatible tanto en ejecución normal como si se empaqueta con PyInstaller (sys._MEIPASS).
    """
    if hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parent
    return base_path / ruta_relativa


# ==============================================================================
# PALETA OFICIAL DE COLORES (TEMA OSCURO MORADO + ROSADO)
# ==============================================================================

COLOR_BG          = "#1A0B2E"  # Fondo principal oscuro
COLOR_CARD        = "#2A1450"  # Fondo de paneles y tarjetas
COLOR_SIDEBAR     = "#220D3E"  # Fondo de la barra lateral
COLOR_PURPLE_MAIN = "#7B2FF7"  # Morado principal
COLOR_PURPLE_LGT  = "#9D4EDD"  # Morado claro
COLOR_PINK_INT    = "#F72585"  # Rosado intenso (acentos y botones principales)
COLOR_PINK_SOFT   = "#FF70A6"  # Rosado suave (destacados y hover)
COLOR_TEXT_MAIN   = "#F5F5FA"  # Texto claro principal
COLOR_TEXT_MUTED  = "#B8B8C8"  # Texto secundario
COLOR_BORDER      = "#3E1E6B"  # Borde sutil de tarjetas
COLOR_GREEN       = "#50FA7B"  # Estado óptimo
COLOR_YELLOW      = "#FFB86C"  # Advertencia
COLOR_RED         = "#FF5555"  # Error o alerta


# ==============================================================================
# BREAKPOINTS Y DIMENSIONES RESPONSIVE
# ==============================================================================

BREAKPOINT_COMPACTO = 900
BREAKPOINT_MEDIO    = 1250

MIN_ANCHO = 800
MIN_ALTO  = 550


def obtener_modo_responsive(ancho: int) -> str:
    """
    Clasifica el ancho actual de la ventana en tres modos responsive:
    - 'compacto': ancho < 900 px
    - 'medio':    900 px <= ancho <= 1250 px
    - 'amplio':   ancho > 1250 px
    """
    if ancho < BREAKPOINT_COMPACTO:
        return "compacto"
    elif ancho <= BREAKPOINT_MEDIO:
        return "medio"
    else:
        return "amplio"


# ==============================================================================
# GESTIÓN CENTRALIZADA DE FUENTES Y ESTILOS TTK
# ==============================================================================

class GestorEstilos:
    """Gestiona la inicialización de estilos ttk y fuentes nombradas escalables."""

    @staticmethod
    def configurar_estilos(root: tk.Tk):
        """Inicializa los temas, fuentes y widgets ttk adaptables."""
        style = ttk.Style(root)
        style.theme_use("clam")

        # Fuentes nombradas escalables
        f_base = tkfont.Font(root=root, family="Segoe UI", size=10, name="BrachioBase")
        f_bold = tkfont.Font(root=root, family="Segoe UI", size=10, weight="bold", name="BrachioBold")
        f_tit  = tkfont.Font(root=root, family="Segoe UI", size=11, weight="bold", name="BrachioTitulo")
        f_cod  = tkfont.Font(root=root, family="Consolas", size=10, name="BrachioCodigo")

        # Altura de filas proporcional a la métrica de la fuente
        altura_fila = f_base.metrics("linespace") + 10

        # Tablas Treeview
        style.configure(
            "Treeview",
            background=COLOR_CARD,
            foreground=COLOR_TEXT_MAIN,
            fieldbackground=COLOR_CARD,
            borderwidth=0,
            font=f_base,
            rowheight=max(26, altura_fila)
        )
        style.configure(
            "Treeview.Heading",
            background=COLOR_SIDEBAR,
            foreground=COLOR_PINK_SOFT,
            font=f_bold,
            relief="flat",
            padding=[6, 6]
        )
        style.map("Treeview", background=[("selected", COLOR_PURPLE_MAIN)], foreground=[("selected", "#FFFFFF")])
        style.map("Treeview.Heading", background=[("active", COLOR_CARD)])

        # Pestañas ttk.Notebook
        style.configure(
            "TNotebook",
            background=COLOR_BG,
            borderwidth=0
        )
        style.configure(
            "TNotebook.Tab",
            background=COLOR_CARD,
            foreground=COLOR_TEXT_MUTED,
            font=f_bold,
            padding=[14, 7]
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", COLOR_PURPLE_MAIN), ("active", COLOR_SIDEBAR)],
            foreground=[("selected", "#FFFFFF"), ("active", COLOR_PINK_SOFT)]
        )

        # Barras de progreso
        style.configure(
            "Brachio.Horizontal.TProgressbar",
            troughcolor=COLOR_SIDEBAR,
            background=COLOR_PINK_INT,
            thickness=12,
            borderwidth=0
        )

        # Barras de desplazamiento
        style.configure(
            "Vertical.TScrollbar",
            troughcolor=COLOR_CARD,
            background=COLOR_SIDEBAR,
            arrowcolor=COLOR_PINK_SOFT,
            relief="flat"
        )
        style.configure(
            "Horizontal.TScrollbar",
            troughcolor=COLOR_CARD,
            background=COLOR_SIDEBAR,
            arrowcolor=COLOR_PINK_SOFT,
            relief="flat"
        )

