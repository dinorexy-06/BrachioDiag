"""
================================================================================
 BrachioDiag - Aplicación de Escritorio con Interfaz Gráfica Nativa Responsive
 Desarrolladora: Angélica Serracín
 Materia: Sistemas Operativos | UTP - Centro Regional de Chiriquí
================================================================================
"""

import os
import sys
import socket
import threading
import queue
import ctypes
import webbrowser
import datetime
import subprocess
import time
from pathlib import Path

# Activar nitidez en pantallas con escalado DPI en Windows (100%, 125%, 150%)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# Identificador de aplicación para que Windows muestre el ícono propio en la barra de tareas
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("BrachioDiag.App")
except Exception:
    pass

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from tkinter import font as tkfont

# Módulos internos del proyecto
import logica
import estilos
from estilos import (
    COLOR_BG, COLOR_CARD, COLOR_SIDEBAR, COLOR_PURPLE_MAIN, COLOR_PURPLE_LGT,
    COLOR_PINK_INT, COLOR_PINK_SOFT, COLOR_TEXT_MAIN, COLOR_TEXT_MUTED,
    COLOR_BORDER, COLOR_GREEN, COLOR_YELLOW, COLOR_RED,
    MIN_ANCHO, MIN_ALTO, ruta_recurso, obtener_modo_responsive
)


# ==============================================================================
# COMPONENTE REUTILIZABLE: TOOLTIP FLOTANTE ELEGANTE
# ==============================================================================

class Tooltip:
    """Tooltip flotante elegante que sigue la paleta temática oscura del proyecto."""
    def __init__(self, widget, texto=""):
        self.widget = widget
        self.texto = texto
        self.tipwindow = None
        self.widget.bind("<Enter>", self.mostrar, add="+")
        self.widget.bind("<Leave>", self.ocultar, add="+")

    def actualizar_texto(self, nuevo_texto):
        self.texto = nuevo_texto
        if self.tipwindow:
            self.ocultar()

    def mostrar(self, event=None):
        if self.tipwindow or not self.texto:
            return
        try:
            x = self.widget.winfo_rootx() + 10
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
            self.tipwindow = tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")
            # Color morado oscuro con borde sutil acorde a la app
            lbl = tk.Label(
                tw,
                text=self.texto,
                justify=tk.LEFT,
                bg="#2A1450",
                fg="#F5F5FA",
                relief=tk.SOLID,
                bd=1,
                highlightthickness=1,
                highlightbackground="#7B2FF7",
                font=("Segoe UI", 9),
                padx=8,
                pady=4
            )
            lbl.pack()
        except Exception:
            pass

    def ocultar(self, event=None):
        if self.tipwindow:
            try:
                self.tipwindow.destroy()
            except Exception:
                pass
            self.tipwindow = None


# ==============================================================================
# COMPONENTE REUTILIZABLE: MARCO CON SCROLL RESPONSIVE (CANVAS + FRAME)
# ==============================================================================

class MarcoConScroll(tk.Frame):
    """
    Contenedor con desplazamiento vertical inteligente y 100% responsive:
    1. El contenido siempre inicia pegado arriba sin espacios vacíos (anchor='nw' en (0, 0)).
    2. Si el contenido cabe en la ventana (alto_contenido <= alto_canvas):
       - La scrollregion se fija en (0, 0, max(fw, cw), max(fh, ch)).
       - La barra de scroll se oculta automáticamente (pack_forget).
       - La rueda del ratón y arrastres se ignoran (yview permanece en (0.0, 1.0)).
    3. Si el contenido supera la altura visible (alto_contenido > alto_canvas):
       - La barra de scroll se muestra a la derecha.
       - La rueda del ratón permite un desplazamiento suave con protección en bordes (sin números negativos).
    4. La rueda del ratón solo desplaza este marco si el cursor está dentro y NO sobre
       un widget que maneje su propio scroll (como Treeview, Text, Listbox o Scrollbar).
    """
    def __init__(self, parent, bg=COLOR_BG, *args, **kwargs):
        super().__init__(parent, bg=bg, *args, **kwargs)
        self.bg = bg
        self._scrollbar_visible = False

        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, borderwidth=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview, style="Vertical.TScrollbar")
        self.interior = tk.Frame(self.canvas, bg=bg)

        # 1. Ventana interna creada estrictamente en (0, 0) con anchor='nw' para que no quede centrada ni desfasada
        self.window_id = self.canvas.create_window((0, 0), window=self.interior, anchor="nw")
        
        # Conectar el reporte de posición del canvas con nuestro actualizador dinámico
        self.canvas.configure(yscrollcommand=self._on_yscroll_actualizado)

        # El canvas ocupa el área disponible; la barra solo se empaquetará si el contenido no cabe
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Escuchar cambios de geometría del contenido y del canvas
        self.interior.bind("<Configure>", self._actualizar_geometria)
        self.canvas.bind("<Configure>", self._al_configurar_canvas)

        # Activar enlace de rueda del ratón solo mientras el puntero está dentro de este componente
        self.canvas.bind("<Enter>", self._activar_scroll_raton)
        self.canvas.bind("<Leave>", self._desactivar_scroll_raton)
        self.interior.bind("<Enter>", self._activar_scroll_raton)
        self.interior.bind("<Leave>", self._desactivar_scroll_raton)

        # Posición inicial garantizada en cero
        self.canvas.yview_moveto(0.0)

    def _on_yscroll_actualizado(self, primero, ultimo):
        """
        Callback invocado por el Canvas al cambiar el rango visible.
        Decide si oculta o muestra la barra de desplazamiento:
        - Si 'primero' <= 0.0 y 'ultimo' >= 1.0, todo el contenido cabe -> oculta la barra.
        - De lo contrario, parte del contenido queda fuera -> muestra la barra.
        """
        self.scrollbar.set(primero, ultimo)
        try:
            p, u = float(primero), float(ultimo)
            cabe = (p <= 0.0 and u >= 1.0)
            if cabe:
                if self._scrollbar_visible:
                    self.scrollbar.pack_forget()
                    self._scrollbar_visible = False
            else:
                if not self._scrollbar_visible:
                    self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y, before=self.canvas)
                    self._scrollbar_visible = True
        except Exception:
            pass

    def _actualizar_geometria(self, event=None):
        """
        Calcula la región de scroll con la fórmula exacta:
        scrollregion = (0, 0, max(ancho_contenido, ancho_canvas), max(alto_contenido, alto_canvas))
        Al usar el máximo con la dimensión del canvas, cuando el contenido cabe, la scrollregion
        coincide exactamente con la ventana visible, impidiendo desplazamientos hacia arriba o abajo.
        """
        try:
            cw = max(1, self.canvas.winfo_width())
            ch = max(1, self.canvas.winfo_height())
            fw = max(1, self.interior.winfo_reqwidth())
            fh = max(1, self.interior.winfo_reqheight())

            if event:
                if event.widget == self.interior:
                    fw = max(fw, event.width)
                    fh = max(fh, event.height)
                elif event.widget == self.canvas:
                    cw = max(cw, event.width)
                    ch = max(ch, event.height)

            sr = (0, 0, max(fw, cw), max(fh, ch))
            self.canvas.configure(scrollregion=sr)

            if fh <= ch:
                # El contenido cabe completo: mantener pegado arriba y retirar barra
                self.canvas.yview_moveto(0.0)
                if self._scrollbar_visible:
                    self.scrollbar.pack_forget()
                    self._scrollbar_visible = False
            else:
                # El contenido excede la ventana: mostrar barra si no estaba visible
                if not self._scrollbar_visible:
                    self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y, before=self.canvas)
                    self._scrollbar_visible = True
        except Exception:
            pass

    def _al_configurar_canvas(self, event):
        """Ajusta el ancho de la ventana interna al ancho visible del canvas."""
        try:
            self.canvas.itemconfig(self.window_id, width=event.width)
            self._actualizar_geometria(event)
        except Exception:
            pass

    def _activar_scroll_raton(self, event=None):
        """Activa el receptor de la rueda del ratón cuando el cursor entra en el área."""
        self.bind_all("<MouseWheel>", self._on_mousewheel)

    def _desactivar_scroll_raton(self, event=None):
        """Desactiva el receptor de la rueda del ratón al salir del área."""
        self.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        """
        Procesa el giro de la rueda del ratón en Windows:
        1. Comprueba si el puntero está sobre este MarcoConScroll.
        2. Si el cursor está sobre un widget con scroll propio (Treeview, Text, Listbox), no desplaza el marco.
        3. Si el contenido cabe en pantalla, no realiza ningún desplazamiento.
        4. Desplaza de forma fluida e impide salir de los límites reales (yview < 0.0).
        """
        # 1. Verificar si el evento ocurrió efectivamente dentro de este MarcoConScroll
        w = event.widget
        adentro = False
        while w:
            if w in (self.canvas, self.interior, self):
                adentro = True
                break
            w = getattr(w, "master", None)
        if not adentro:
            return

        # 2. Si está sobre un componente que tiene su propio scroll, dejar que ese componente se mueva
        w = event.widget
        while w and w not in (self.canvas, self.interior, self):
            if isinstance(w, (ttk.Treeview, tk.Text, tk.Listbox, ttk.Scrollbar, tk.Scrollbar)):
                return
            w = getattr(w, "master", None)

        # 3. Si el contenido cabe completamente, no mover nada
        fh = self.interior.winfo_reqheight()
        ch = self.canvas.winfo_height()
        if fh <= ch:
            self.canvas.yview_moveto(0.0)
            return

        # 4. Desplazamiento de unidades con protección estricta en el borde superior
        try:
            delta = event.delta
            unidades = int(-1 * (delta / 120))
            self.canvas.yview_scroll(unidades, "units")
            if self.canvas.yview()[0] < 0.0:
                self.canvas.yview_moveto(0.0)
        except Exception:
            pass

    def scroll_arriba(self):
        """Regresa el scroll exactamente a la parte superior (0.0)."""
        self.canvas.yview_moveto(0.0)


# ==============================================================================
# CLASE PRINCIPAL: BRACHIODIAG
# ==============================================================================

class BrachioDiagApp(tk.Tk):
    """
    Aplicación de escritorio principal BrachioDiag.
    Totalmente responsive con breakpoints, menú adaptable, logos integrados y temas visuales.
    """
    def __init__(self):
        super().__init__()

        self.title("BrachioDiag")
        self.configure(bg=COLOR_BG)
        self.minsize(MIN_ANCHO, MIN_ALTO)

        # Inicializar estilos ttk centralizados
        estilos.GestorEstilos.configurar_estilos(self)

        # Estado responsive y debounce
        self.modo_responsive_actual = "medio"
        self._debounce_timer = None
        self._pantalla_completa = False

        # Diccionario para almacenar resultados de herramientas ejecutadas
        self.datos_sesion = {
            "sistema": None,
            "discos": None,
            "archivos_pesados": None,
            "programas": None,
            "inicio": None,
            "errores": None,
            "red": None,
            "rendimiento": None,
            "respaldo": None,
            "envio": None,
            "permisos": None,
            "salud": None
        }

        # Control del monitor de rendimiento
        self.monitor_activo = False
        self.monitor_pausado = False
        self.historial_cpu = [0.0] * 60
        self.historial_ram = [0.0] * 60
        self.despacho_monitor_id = None

        # Control de tareas asíncronas
        self.cancel_event_pesados = None

        # UI y navegación
        self.botones_sidebar = {}
        self.seccion_activa = "1"
        self.menu_visible_escritorio = True   # Preferencia del usuario en modo amplio y medio (abierto por defecto)
        self.menu_overlay_abierto = False     # Estado del menú superpuesto en modo compacto (cerrado por defecto)

        # Referencias a imágenes (para evitar recolección de basura)
        self.img_logo_grande = None
        self.img_logo_grande_sub = None
        self.img_logo_pequeno = None
        self.img_logo_pequeno_sub = None

        # Cargar recursos gráficos e íconos oficiales
        self._cargar_recursos_graficos()

        # Configurar tamaño inicial relativo a la pantalla (80-85% centrado)
        self._configurar_geometria_inicial()

        # Construir estructura base de la interfaz
        self._construir_interfaz_base()

        # Escuchar cambios de tamaño de ventana con debounce
        self.bind("<Configure>", self._al_recibir_configure)
        self.bind("<F11>", self._toggle_fullscreen)
        self.bind("<Control-m>", lambda e: self._alternar_menu_lateral_manual())
        self.bind("<Control-M>", lambda e: self._alternar_menu_lateral_manual())
        self.bind("<Escape>", self._on_escape_tecla)

        # Confirmación de salida
        self.protocol("WM_DELETE_WINDOW", self._confirmar_salida)

        # Cargar pantalla inicial (Herramienta 1)
        self._mostrar_herramienta_1()

    # ==========================================================================
    # CARGA DE RECURSOS Y GEOMETRÍA INICIAL
    # ==========================================================================

    def _cargar_recursos_graficos(self):
        """Carga los logos e íconos oficiales de assets/ con fallbacks seguros."""
        # 1. Ícono de la ventana y barra de tareas (.ico)
        ruta_ico = ruta_recurso("assets/icono.ico")
        if ruta_ico.exists():
            try:
                self.iconbitmap(str(ruta_ico))
            except Exception:
                pass

        # 2. Logo pequeño (emblema oficial 64x64)
        ruta_p = ruta_recurso("assets/logo_pequeno.png")
        if ruta_p.exists():
            try:
                self.img_logo_pequeno = tk.PhotoImage(file=str(ruta_p))
                self.img_logo_pequeno_sub = self.img_logo_pequeno.subsample(2, 2)
                # Como respaldo para el ícono de la ventana
                self.iconphoto(True, self.img_logo_pequeno)
            except Exception:
                self.img_logo_pequeno = None
                self.img_logo_pequeno_sub = None

        # 3. Logo grande (emblema oficial 420px)
        ruta_g = ruta_recurso("assets/logo_grande.png")
        if ruta_g.exists():
            try:
                self.img_logo_grande = tk.PhotoImage(file=str(ruta_g))
                self.img_logo_grande_sub = self.img_logo_grande.subsample(2, 2)
            except Exception:
                self.img_logo_grande = None
                self.img_logo_grande_sub = None

    def _configurar_geometria_inicial(self):
        """Calcula un tamaño inicial relativo a la resolución de la pantalla (80-85%)."""
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()

        ancho = max(MIN_ANCHO, min(int(sw * 0.82), 1380))
        alto = max(MIN_ALTO, min(int(sh * 0.82), 880))

        x = max(0, (sw - ancho) // 2)
        y = max(0, (sh - alto) // 2)

        self.geometry(f"{ancho}x{alto}+{x}+{y}")
        self.modo_responsive_actual = obtener_modo_responsive(ancho)

    def _toggle_fullscreen(self, event=None):
        """Alterna el modo de pantalla completa al presionar F11."""
        self._pantalla_completa = not self._pantalla_completa
        self.attributes("-fullscreen", self._pantalla_completa)

    # ==========================================================================
    # MANEJO RESPONSIVE CENTRALIZADO (DEBOUNCE Y BREAKPOINTS)
    # ==========================================================================

    def _al_recibir_configure(self, event):
        """Captura el evento Configure de la ventana raíz y programa el debounce."""
        if event.widget == self:
            if self._debounce_timer:
                self.after_cancel(self._debounce_timer)
            self._debounce_timer = self.after(100, self._procesar_cambio_tamano)

    def _procesar_cambio_tamano(self):
        """Determina si cambió el modo responsive y actualiza los componentes que lo requieran."""
        self._debounce_timer = None
        ancho_actual = self.winfo_width()
        nuevo_modo = obtener_modo_responsive(ancho_actual)

        cambio_modo = (nuevo_modo != self.modo_responsive_actual)
        self.modo_responsive_actual = nuevo_modo

        # Actualizar componentes base
        self._adaptar_encabezado_responsive(nuevo_modo)
        self._adaptar_sidebar_responsive(nuevo_modo)
        self._actualizar_geometria_sidebar()

        # Actualizar geometría y barra de scroll de la pantalla activa
        if hasattr(self, "scroll_activo") and self.scroll_activo:
            try:
                self.scroll_activo._actualizar_geometria()
            except Exception:
                pass

        # Notificar a la pantalla activa si implementa adaptador responsive
        if hasattr(self, "_redibujar_pantalla_activa_responsive"):
            self._redibujar_pantalla_activa_responsive(nuevo_modo, ancho_actual, cambio_modo)

    # ==========================================================================
    # CONSTRUCCIÓN DE LA INTERFAZ BASE
    # ==========================================================================

    def _construir_interfaz_base(self):
        """Crea el Encabezado superior con altura dinámica, Menú lateral adaptable, Área central y Pie."""
        # 1. ENCABEZADO SUPERIOR RESPONSIVE (Sin altura fija; se adapta al contenido)
        self.header_frame = tk.Frame(self, bg=COLOR_SIDEBAR)
        self.header_frame.pack(side=tk.TOP, fill=tk.X)
        self.header_frame.columnconfigure(0, weight=0)  # Botón ☰
        self.header_frame.columnconfigure(1, weight=0)  # Logo
        self.header_frame.columnconfigure(2, weight=1)  # Título y subtítulo
        self.header_frame.columnconfigure(3, weight=0)  # Estado BOSGAME
        self.header_frame.rowconfigure(0, weight=1)

        # Botón hamburguesa '☰' para alternar menú lateral (área cómoda >= 40x40 px)
        self.btn_toggle_menu = tk.Button(
            self.header_frame,
            text="☰",
            font=("Segoe UI", 13, "bold"),
            bg=COLOR_SIDEBAR,
            fg=COLOR_PINK_SOFT,
            activebackground=COLOR_CARD,
            activeforeground="#FFFFFF",
            bd=0,
            width=3,
            cursor="hand2",
            command=self._alternar_menu_lateral_manual
        )
        self.btn_toggle_menu.grid(row=0, column=0, padx=(10, 6), pady=8, sticky="ns")
        self.tooltip_btn_menu = Tooltip(self.btn_toggle_menu, "Mostrar u ocultar menú (Ctrl+M)")
        
        self.btn_toggle_menu.bind("<Enter>", lambda e: self.btn_toggle_menu.config(bg=COLOR_CARD, fg=COLOR_PINK_SOFT))
        self.btn_toggle_menu.bind("<Leave>", lambda e: self._actualizar_estilo_btn_menu())

        # Logo emblema pequeño (64x64 px)
        self.lbl_logo_header = tk.Label(self.header_frame, bg=COLOR_SIDEBAR)
        if self.img_logo_pequeno:
            self.lbl_logo_header.config(image=self.img_logo_pequeno)
        else:
            self.lbl_logo_header.config(text="🦕", font=("Segoe UI Emoji", 20), fg=COLOR_PINK_SOFT)
        self.lbl_logo_header.grid(row=0, column=1, padx=(4, 10), pady=8, sticky="w")

        # Textos de título y subtítulo dinámico
        self.f_tit_header = tk.Frame(self.header_frame, bg=COLOR_SIDEBAR)
        self.f_tit_header.grid(row=0, column=2, sticky="w", padx=4, pady=6)

        self.lbl_header_titulo = tk.Label(
            self.f_tit_header,
            text="BrachioDiag",
            font=("Segoe UI", 15, "bold"),
            fg=COLOR_PINK_SOFT,
            bg=COLOR_SIDEBAR,
            anchor="w"
        )
        self.lbl_header_titulo.pack(anchor="w")

        self.lbl_header_sub = tk.Label(
            self.f_tit_header,
            text="Desarrolladora: Angélica Serracín | UTP - Sistemas Operativos",
            font=("Segoe UI", 10),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_SIDEBAR,
            anchor="w"
        )
        self.lbl_header_sub.pack(anchor="w")

        # Indicador BOSGAME a la derecha con tooltip flotante
        self.lbl_header_bosgame = tk.Label(
            self.header_frame,
            text="● BOSGAME: Sin conexión",
            font=("Segoe UI", 10, "bold"),
            fg=COLOR_YELLOW,
            bg=COLOR_SIDEBAR,
            anchor="e",
            cursor="hand2"
        )
        self.lbl_header_bosgame.grid(row=0, column=3, padx=(10, 16), pady=8, sticky="e")
        self.tooltip_bosgame = Tooltip(self.lbl_header_bosgame, "BOSGAME: Sin conexión (192.168.100.10)")

        tk.Frame(self, bg=COLOR_BORDER, height=1).pack(side=tk.TOP, fill=tk.X)

        # 2. PIE DE PÁGINA
        self.footer_frame = tk.Frame(self, bg=COLOR_SIDEBAR, height=34)
        self.footer_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.footer_frame.pack_propagate(False)

        tk.Frame(self, bg=COLOR_BORDER, height=1).pack(side=tk.BOTTOM, fill=tk.X)

        self.lbl_estado = tk.Label(
            self.footer_frame,
            text="[Listo] Aplicación iniciada.",
            font=("Segoe UI", 10),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_SIDEBAR,
            anchor="w"
        )
        self.lbl_estado.pack(side=tk.LEFT, padx=14, fill=tk.X, expand=True)

        self.progreso_bar = ttk.Progressbar(
            self.footer_frame,
            style="Brachio.Horizontal.TProgressbar",
            mode="determinate",
            length=160
        )
        self.progreso_bar.pack(side=tk.RIGHT, padx=14, pady=8)

        # 3. CUERPO (SIDEBAR + CENTRO + TELÓN DE FONDO PARA OVERLAY)
        self.body_frame = tk.Frame(self, bg=COLOR_BG)
        self.body_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Telón de fondo para cerrar el menú superpuesto en modo compacto al hacer clic fuera
        self.overlay_backdrop = tk.Frame(self.body_frame, bg="#0B0517")
        self.overlay_backdrop.bind("<Button-1>", lambda e: self._cerrar_menu_overlay())

        # Contenedor del menú lateral con Canvas y scroll vertical propio
        self.sidebar_container = tk.Frame(self.body_frame, bg=COLOR_SIDEBAR)
        self.sidebar_container.pack_propagate(False)
        self._sidebar_scroll_visible = False

        self.canvas_sidebar = tk.Canvas(self.sidebar_container, bg=COLOR_SIDEBAR, highlightthickness=0)
        self.scroll_sidebar = ttk.Scrollbar(self.sidebar_container, orient="vertical", command=self.canvas_sidebar.yview, style="Vertical.TScrollbar")
        self.f_sidebar_content = tk.Frame(self.canvas_sidebar, bg=COLOR_SIDEBAR)

        self.win_sidebar_id = self.canvas_sidebar.create_window((0, 0), window=self.f_sidebar_content, anchor="nw")
        self.canvas_sidebar.configure(yscrollcommand=self._on_sidebar_yscroll)

        self.f_sidebar_content.bind("<Configure>", self._actualizar_geometria_sidebar)
        self.canvas_sidebar.bind("<Configure>", self._al_configurar_canvas_sidebar)

        # Eventos para scroll con rueda de ratón en el menú lateral
        self.canvas_sidebar.bind("<Enter>", lambda e: self._activar_scroll_sidebar())
        self.canvas_sidebar.bind("<Leave>", lambda e: self._desactivar_scroll_sidebar())
        self.f_sidebar_content.bind("<Enter>", lambda e: self._activar_scroll_sidebar())
        self.f_sidebar_content.bind("<Leave>", lambda e: self._desactivar_scroll_sidebar())

        self.canvas_sidebar.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Separador vertical
        self.v_separator = tk.Frame(self.body_frame, bg=COLOR_BORDER, width=1)

        # Área central donde se renderizan las herramientas
        self.center_frame = tk.Frame(self.body_frame, bg=COLOR_BG)
        self.center_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Construir botones de navegación
        self._construir_menu_lateral()

    def _on_sidebar_yscroll(self, primero, ultimo):
        """Actualiza la barra de scroll del menú y solo la muestra si el contenido no cabe."""
        self.scroll_sidebar.set(primero, ultimo)
        try:
            p, u = float(primero), float(ultimo)
            cabe = (p <= 0.0 and u >= 1.0)
            if cabe:
                if self._sidebar_scroll_visible:
                    self.scroll_sidebar.pack_forget()
                    self._sidebar_scroll_visible = False
            else:
                if not self._sidebar_scroll_visible:
                    self.scroll_sidebar.pack(side=tk.RIGHT, fill=tk.Y, before=self.canvas_sidebar)
                    self._sidebar_scroll_visible = True
        except Exception:
            pass

    def _actualizar_geometria_sidebar(self, event=None):
        """Calcula la scrollregion exacta del sidebar: (0, 0, max(fw, cw), max(fh, ch))."""
        try:
            cw = max(1, self.canvas_sidebar.winfo_width())
            ch = max(1, self.canvas_sidebar.winfo_height())
            fw = max(1, self.f_sidebar_content.winfo_reqwidth())
            fh = max(1, self.f_sidebar_content.winfo_reqheight())

            if event:
                if event.widget == self.f_sidebar_content:
                    fw = max(fw, event.width)
                    fh = max(fh, event.height)
                elif event.widget == self.canvas_sidebar:
                    cw = max(cw, event.width)
                    ch = max(ch, event.height)

            sr = (0, 0, max(fw, cw), max(fh, ch))
            self.canvas_sidebar.configure(scrollregion=sr)

            if fh <= ch:
                self.canvas_sidebar.yview_moveto(0.0)
                if self._sidebar_scroll_visible:
                    self.scroll_sidebar.pack_forget()
                    self._sidebar_scroll_visible = False
            else:
                if not self._sidebar_scroll_visible:
                    self.scroll_sidebar.pack(side=tk.RIGHT, fill=tk.Y, before=self.canvas_sidebar)
                    self._sidebar_scroll_visible = True
        except Exception:
            pass

    def _al_configurar_canvas_sidebar(self, event):
        try:
            self.canvas_sidebar.itemconfig(self.win_sidebar_id, width=event.width)
            self._actualizar_geometria_sidebar(event)
        except Exception:
            pass

    def _activar_scroll_sidebar(self):
        self.bind_all("<MouseWheel>", self._on_mousewheel_sidebar)

    def _desactivar_scroll_sidebar(self):
        self.unbind_all("<MouseWheel>")

    def _on_mousewheel_sidebar(self, event):
        if not hasattr(self, "canvas_sidebar"):
            return

        # 1. Comprobar que el puntero esté efectivamente sobre la barra lateral
        w = event.widget
        adentro = False
        while w:
            if w in (self.canvas_sidebar, self.f_sidebar_content, self.sidebar_container):
                adentro = True
                break
            w = getattr(w, "master", None)
        if not adentro:
            return

        # 2. Si las opciones caben en la altura de la ventana, no desplazar
        fh = self.f_sidebar_content.winfo_reqheight()
        ch = self.canvas_sidebar.winfo_height()
        if fh <= ch:
            self.canvas_sidebar.yview_moveto(0.0)
            return

        # 3. Desplazamiento fluido con protección en el tope superior
        try:
            delta = event.delta
            unidades = int(-1 * (delta / 120))
            self.canvas_sidebar.yview_scroll(unidades, "units")
            if self.canvas_sidebar.yview()[0] < 0.0:
                self.canvas_sidebar.yview_moveto(0.0)
        except Exception:
            pass

    def _calcular_ancho_optimo_menu(self):
        """Calcula dinámicamente el ancho necesario para que ningún nombre se corte."""
        try:
            fuent = tkfont.Font(font=("Segoe UI", 10))
            ancho_max_texto = 0
            for clave, icono, texto, cmd in self.herramientas_def:
                linea = f"{icono}   {texto}"
                w = fuent.measure(linea)
                if w > ancho_max_texto:
                    ancho_max_texto = w

            # Padding de botón (24px) + barra de scroll (16px) + márgenes internos (24px)
            ancho_necesario = ancho_max_texto + 64

            # Límite máximo: 45% del ancho de la ventana
            w_ventana = self.winfo_width()
            limite_max = int(w_ventana * 0.45) if w_ventana > 200 else 320
            ancho_final = max(240, min(ancho_necesario, max(260, limite_max)))
            return ancho_final
        except Exception:
            return 265

    def _construir_menu_lateral(self):
        """Crea los botones de las herramientas con ancho dinámico y soporte wraplength."""
        self.herramientas_def = [
            ("1", "🏠", "1. Inicio e información", self._mostrar_herramienta_1),
            ("2", "📈", "2. Monitor rendimiento", self._mostrar_herramienta_2),
            ("3", "💽", "3. Discos y archivos", self._mostrar_herramienta_3),
            ("4", "⚙", "4. Programas y errores", self._mostrar_herramienta_4),
            ("5", "🌐", "5. Configuración IP", self._mostrar_herramienta_5),
            ("6", "🔌", "6. Conexión a BOSGAME", self._mostrar_herramienta_6),
            ("7", "🗜", "7. Respaldo de carpetas", self._mostrar_herramienta_7),
            ("8", "📝", "8. Editor y envío", self._mostrar_herramienta_8),
            ("9", "🔒", "9. Permisos de archivos", self._mostrar_herramienta_9),
            ("10", "📄", "10. Informe diagnóstico", self._mostrar_herramienta_10),
            ("acerca", "ℹ", "Acerca de", self._mostrar_acerca_de),
            ("salir", "🚪", "Salir", self._confirmar_salida),
        ]

        self.lbl_tit_sidebar = tk.Label(
            self.f_sidebar_content,
            text="HERRAMIENTAS",
            font=("Segoe UI", 10, "bold"),
            fg=COLOR_PINK_SOFT,
            bg=COLOR_SIDEBAR
        )
        self.lbl_tit_sidebar.pack(anchor="w", padx=14, pady=(12, 6))

        ancho_optimo = self._calcular_ancho_optimo_menu()
        w_wrap = max(180, ancho_optimo - 45)

        for clave, icono, texto, comando in self.herramientas_def:
            def _crear_cmd(cmd):
                def _ejecutar():
                    cmd()
                    # Si el overlay estaba abierto en modo compacto, cerrarlo al seleccionar
                    if self.modo_responsive_actual == "compacto" and self.menu_overlay_abierto:
                        self._cerrar_menu_overlay()
                return _ejecutar

            btn = tk.Button(
                self.f_sidebar_content,
                text=f"{icono}   {texto}",
                font=("Segoe UI", 10),
                fg=COLOR_TEXT_MAIN,
                bg=COLOR_SIDEBAR,
                activebackground=COLOR_CARD,
                activeforeground=COLOR_PINK_SOFT,
                bd=0,
                padx=10,
                pady=6,
                anchor="w",
                justify="left",
                wraplength=w_wrap,
                cursor="hand2",
                command=_crear_cmd(comando)
            )
            btn.pack(fill=tk.X, padx=4, pady=1)

            btn.bind("<Enter>", lambda e, b=btn, k=clave: self._hover_enter(b, k))
            btn.bind("<Leave>", lambda e, b=btn, k=clave: self._hover_leave(b, k))
            btn.bind("<MouseWheel>", self._on_mousewheel_sidebar)

            self.botones_sidebar[clave] = {
                "widget": btn,
                "icono": icono,
                "texto": texto
            }

    # ==========================================================================
    # ADAPTACIONES RESPONSIVE (HEADER Y SIDEBAR)
    # ==========================================================================

    def _adaptar_encabezado_responsive(self, modo):
        """Ajusta el tamaño del emblema y subtítulos garantizando que nunca se corten."""
        # 1. Logo del encabezado (completo 64x64 en amplio/medio, subsample 32x32 en compacto)
        if modo == "compacto":
            if self.img_logo_pequeno_sub:
                self.lbl_logo_header.config(image=self.img_logo_pequeno_sub)
        else:
            if self.img_logo_pequeno:
                self.lbl_logo_header.config(image=self.img_logo_pequeno)

        # 2. Subtítulo dinámico medido con font.measure()
        texto_amplio = "Desarrolladora: Angélica Serracín | UTP - Sistemas Operativos"
        texto_medio = "Angélica Serracín · Sistemas Operativos"

        if modo == "compacto":
            self.lbl_header_sub.pack_forget()
        else:
            try:
                fuent_sub = tkfont.Font(font=("Segoe UI", 10))
                w_amplio = fuent_sub.measure(texto_amplio)
                ancho_ventana = self.winfo_width()
                # Espacio libre restando botón, logo, bosgame y márgenes
                espacio_libre = ancho_ventana - 340
                if modo == "amplio" and espacio_libre >= w_amplio:
                    self.lbl_header_sub.config(text=texto_amplio)
                else:
                    self.lbl_header_sub.config(text=texto_medio)
            except Exception:
                self.lbl_header_sub.config(text=texto_amplio if modo == "amplio" else texto_medio)

            if not self.lbl_header_sub.winfo_ismapped():
                self.lbl_header_sub.pack(anchor="w")

        # 3. Indicador BOSGAME adaptable con tooltip completo
        self._actualizar_badge_bosgame()

    def _adaptar_sidebar_responsive(self, modo):
        """Ajusta el menú lateral dinámicamente según el modo (amplio, medio, compacto)."""
        ancho_optimo = self._calcular_ancho_optimo_menu()
        self.sidebar_container.config(width=ancho_optimo)

        # Actualizar wraplength de todos los botones para que nunca se trunquen con puntos suspensivos
        w_wrap = max(180, ancho_optimo - 45)
        for clave, item in self.botones_sidebar.items():
            item["widget"].config(wraplength=w_wrap)

        if modo == "compacto":
            # En modo compacto el sidebar acoplado se oculta para dar 100% de espacio al contenido
            self.sidebar_container.pack_forget()
            if hasattr(self, "v_separator"):
                self.v_separator.pack_forget()

            # Si el overlay estaba abierto, mantener su posición
            if self.menu_overlay_abierto:
                self.sidebar_container.place(relx=0, rely=0, relheight=1.0, width=ancho_optimo)
                self.sidebar_container.lift()
        else:
            # Si veníamos de modo compacto con overlay abierto, cerrarlo
            if self.menu_overlay_abierto:
                self._cerrar_menu_overlay()

            # En modo amplio y medio, respetar la preferencia del usuario
            if self.menu_visible_escritorio:
                self.sidebar_container.pack(side=tk.LEFT, fill=tk.Y, before=self.center_frame)
                if hasattr(self, "v_separator"):
                    self.v_separator.pack(side=tk.LEFT, fill=tk.Y, before=self.center_frame)
            else:
                self.sidebar_container.pack_forget()
                if hasattr(self, "v_separator"):
                    self.v_separator.pack_forget()

        self._actualizar_estilo_btn_menu()

    def _alternar_menu_lateral_manual(self):
        """El botón '☰' muestra u oculta el menú (acoplado en escritorio o superpuesto en compacto)."""
        if self.modo_responsive_actual == "compacto":
            self._toggle_menu_overlay_compacto()
        else:
            self.menu_visible_escritorio = not self.menu_visible_escritorio
            self._adaptar_sidebar_responsive(self.modo_responsive_actual)
            self._actualizar_geometria_sidebar()
            # Redibujar la pantalla activa para que gráficos Canvas aprovechen el nuevo ancho
            if hasattr(self, "_redibujar_pantalla_activa_responsive"):
                self._redibujar_pantalla_activa_responsive(self.modo_responsive_actual, self.winfo_width(), True)
            if hasattr(self, "scroll_activo") and self.scroll_activo:
                try:
                    self.scroll_activo._actualizar_geometria()
                except Exception:
                    pass

    def _toggle_menu_overlay_compacto(self):
        """Abre o cierra el panel superpuesto en modo compacto."""
        if self.menu_overlay_abierto:
            self._cerrar_menu_overlay()
        else:
            self._abrir_menu_overlay()

    def _abrir_menu_overlay(self):
        """Despliega el menú lateral como un panel superpuesto sobre el contenido."""
        self.menu_overlay_abierto = True
        ancho_optimo = self._calcular_ancho_optimo_menu()
        self.sidebar_container.config(width=ancho_optimo)

        # 1. Telón de fondo oscuro clicable
        self.overlay_backdrop.place(relx=0, rely=0, relwidth=1.0, relheight=1.0)
        self.overlay_backdrop.lift()

        # 2. Sidebar superpuesto
        self.sidebar_container.place(relx=0, rely=0, relheight=1.0, width=ancho_optimo)
        self.sidebar_container.lift()

        self._actualizar_estilo_btn_menu()

    def _cerrar_menu_overlay(self):
        """Cierra el panel superpuesto en modo compacto."""
        self.menu_overlay_abierto = False
        try:
            self.sidebar_container.place_forget()
            self.overlay_backdrop.place_forget()
        except Exception:
            pass
        self._actualizar_estilo_btn_menu()

    def _on_escape_tecla(self, event=None):
        """Al presionar Esc, cierra el menú superpuesto si está abierto, o sale de pantalla completa."""
        if self.modo_responsive_actual == "compacto" and self.menu_overlay_abierto:
            self._cerrar_menu_overlay()
            return "break"
        elif self._pantalla_completa:
            self._toggle_fullscreen()
            return "break"

    def _actualizar_estilo_btn_menu(self):
        """Resalta el botón ☰ cuando el menú lateral está visible."""
        visible = False
        if self.modo_responsive_actual == "compacto":
            visible = self.menu_overlay_abierto
        else:
            visible = self.menu_visible_escritorio

        if visible:
            self.btn_toggle_menu.config(
                bg=COLOR_CARD,
                fg=COLOR_PINK_SOFT,
                relief=tk.SOLID,
                bd=1
            )
        else:
            self.btn_toggle_menu.config(
                bg=COLOR_SIDEBAR,
                fg=COLOR_TEXT_MAIN,
                relief=tk.FLAT,
                bd=0
            )

    def _hover_enter(self, boton, clave):
        if self.seccion_activa != clave:
            boton.config(bg=COLOR_CARD, fg=COLOR_PINK_SOFT)

    def _hover_leave(self, boton, clave):
        if self.seccion_activa != clave:
            boton.config(bg=COLOR_SIDEBAR, fg=COLOR_TEXT_MAIN)

    def _resaltar_boton_activo(self, clave):
        """Resalta en rosado intenso el botón de la sección activa."""
        self._detener_monitor_si_activo()
        self.seccion_activa = clave

        for k, item in self.botones_sidebar.items():
            btn = item["widget"]
            if k == clave:
                btn.config(bg=COLOR_PINK_INT, fg="#FFFFFF", font=("Segoe UI", 10, "bold"))
            else:
                btn.config(bg=COLOR_SIDEBAR, fg=COLOR_TEXT_MAIN, font=("Segoe UI", 10))

    def _detener_monitor_si_activo(self):
        """Detiene de inmediato la actualización de CPU/RAM al salir de la pantalla 2."""
        if self.monitor_activo:
            self.monitor_activo = False
            if self.despacho_monitor_id:
                try:
                    self.after_cancel(self.despacho_monitor_id)
                except Exception:
                    pass
                self.despacho_monitor_id = None

    def actualizar_estado(self, mensaje: str, porcentaje: int = None, color=COLOR_TEXT_MUTED):
        """Actualiza la barra de estado inferior."""
        hora = datetime.datetime.now().strftime("%H:%M:%S")
        self.lbl_estado.config(text=f"[{hora}] {mensaje}", fg=color)
        if porcentaje is not None:
            self.progreso_bar["value"] = porcentaje
        self.update_idletasks()

    def _actualizar_badge_bosgame(self):
        """Actualiza el indicador en el encabezado."""
        if logica.estado_bosgame.conectado:
            self.lbl_header_bosgame.config(
                text=f"● BOSGAME: Conectado ({logica.estado_bosgame.ip})",
                fg=COLOR_GREEN
            )
        else:
            self.lbl_header_bosgame.config(
                text="● BOSGAME: Sin conexión",
                fg=COLOR_YELLOW
            )

    def despachar_hilo_principal(self, fn):
        """Ejecuta una función en el hilo principal de forma segura sin excepciones si la ventana se cerró."""
        try:
            if self.winfo_exists():
                self.after(0, fn)
        except Exception:
            pass

    def _limpiar_panel_central(self):
        """Limpia el área central para dibujar una nueva vista y resetea el scroll al inicio."""
        try:
            self.unbind_all("<MouseWheel>")
        except Exception:
            pass
        if hasattr(self, "scroll_activo") and self.scroll_activo:
            try:
                self.scroll_activo.scroll_arriba()
            except Exception:
                pass
            self.scroll_activo = None
        for widget in self.center_frame.winfo_children():
            widget.destroy()

    def _crear_tarjeta(self, parent, titulo="", icono=""):
        """Genera un contenedor tipo tarjeta con estilo morado oscuro y borde sutil."""
        card = tk.Frame(parent, bg=COLOR_CARD, highlightbackground=COLOR_BORDER, highlightthickness=1)
        card.pack(fill=tk.X, pady=8, padx=6)

        if titulo:
            head = tk.Frame(card, bg=COLOR_CARD)
            head.pack(fill=tk.X, padx=14, pady=(10, 6))

            tit_text = f"{icono}  {titulo}" if icono else titulo
            tk.Label(
                head,
                text=tit_text,
                font=("Segoe UI", 11, "bold"),
                fg=COLOR_PINK_SOFT,
                bg=COLOR_CARD
            ).pack(side=tk.LEFT)

            tk.Frame(card, bg=COLOR_BORDER, height=1).pack(fill=tk.X, padx=14, pady=(0, 8))

        return card

    # ==========================================================================
    # HERRAMIENTA 1: INICIO E INFORMACIÓN GENERAL
    # ==========================================================================

    def _mostrar_herramienta_1(self):
        """Pantalla de inicio con logo oficial grande, tacómetro semicircular e información del sistema."""
        self._resaltar_boton_activo("1")
        self._limpiar_panel_central()

        self.scroll_activo = scroll_box = MarcoConScroll(self.center_frame)
        scroll_box.pack(fill=tk.BOTH, expand=True)
        content = scroll_box.interior

        # 1. Cabecera con Logo Oficial Grande
        c_bienvenida = self._crear_tarjeta(content)
        f_b = tk.Frame(c_bienvenida, bg=COLOR_CARD)
        f_b.pack(fill=tk.X, padx=16, pady=12)

        # Mostrar Logo Grande (subsample según modo)
        self.lbl_logo_inicio = tk.Label(f_b, bg=COLOR_CARD)
        if self.img_logo_grande:
            # En modo compacto usar versión reducida subsample(2)
            if self.modo_responsive_actual == "compacto" and self.img_logo_grande_sub:
                self.lbl_logo_inicio.config(image=self.img_logo_grande_sub)
            else:
                self.lbl_logo_inicio.config(image=self.img_logo_grande)
        else:
            self.lbl_logo_inicio.config(text="🦕", font=("Segoe UI Emoji", 48), fg=COLOR_PINK_SOFT)
        self.lbl_logo_inicio.pack(anchor="center", pady=(4, 6))

        tk.Label(
            f_b,
            text="BrachioDiag",
            font=("Segoe UI", 18, "bold"),
            fg=COLOR_PINK_SOFT,
            bg=COLOR_CARD
        ).pack(anchor="center")

        tk.Label(
            f_b,
            text="Herramienta de diagnóstico para Windows",
            font=("Segoe UI", 10),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_CARD
        ).pack(anchor="center", pady=(2, 0))

        # 2. Tacómetro Semicircular de Salud (Canvas)
        c_salud = self._crear_tarjeta(content, "PUNTAJE DE SALUD GLOBAL DEL SISTEMA", "⚡")
        self.f_salud_contenedor = tk.Frame(c_salud, bg=COLOR_CARD)
        self.f_salud_contenedor.pack(fill=tk.X, padx=16, pady=(0, 14))

        if not self.datos_sesion["sistema"]:
            self.datos_sesion["sistema"] = logica.accion_info_general()
            self.datos_sesion["discos"] = logica.accion_espacio_disco()
            self.datos_sesion["red"] = logica.accion_configuracion_ip()

        score, estado, explicaciones = logica.calcular_puntaje_salud(
            self.datos_sesion["sistema"],
            self.datos_sesion["discos"],
            self.datos_sesion["red"],
            logica.estado_bosgame.conectado
        )
        self.datos_sesion["salud"] = (score, estado, explicaciones)

        color_gauge = COLOR_GREEN if score >= 85 else (COLOR_YELLOW if score >= 65 else COLOR_PINK_INT)

        # Tacómetro Canvas adaptable
        box_g = tk.Frame(self.f_salud_contenedor, bg=COLOR_CARD)
        box_g.pack(side=tk.LEFT, padx=10)

        self.canvas_gauge_inicio = tk.Canvas(box_g, width=180, height=110, bg=COLOR_CARD, highlightthickness=0)
        self.canvas_gauge_inicio.pack()

        # Dibujar arco
        self.canvas_gauge_inicio.create_arc(15, 15, 165, 165, start=0, extent=180, style="arc", outline="#3E1E6B", width=14)
        angulo = int((score / 100.0) * 180)
        self.canvas_gauge_inicio.create_arc(15, 15, 165, 165, start=180, extent=-angulo, style="arc", outline=color_gauge, width=14)
        self.canvas_gauge_inicio.create_text(90, 72, text=f"{score}%", fill=COLOR_TEXT_MAIN, font=("Segoe UI", 20, "bold"))
        self.canvas_gauge_inicio.create_text(90, 96, text=estado, fill=color_gauge, font=("Segoe UI", 10, "bold"))

        f_exp = tk.Frame(self.f_salud_contenedor, bg=COLOR_CARD)
        f_exp.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20)

        tk.Label(f_exp, text="Factores evaluados por el algoritmo:", font=("Segoe UI", 10, "bold"), fg=COLOR_PINK_SOFT, bg=COLOR_CARD).pack(anchor="w")
        for e in explicaciones:
            tk.Label(f_exp, text=f"• {e}", font=("Segoe UI", 10), fg=COLOR_TEXT_MAIN, bg=COLOR_CARD).pack(anchor="w", pady=1)

        # 3. Tarjeta de Información General del Sistema y Usuario
        c_info = self._crear_tarjeta(content, "INFORMACIÓN DEL EQUIPO Y DEL USUARIO", "💻")
        self.f_info_grid = tk.Frame(c_info, bg=COLOR_CARD)
        self.f_info_grid.pack(fill=tk.X, padx=16, pady=(0, 14))

        sis = self.datos_sesion["sistema"]
        ram = sis.get("ram", {})
        discos = self.datos_sesion["discos"]
        disco_c = next((d for d in discos if d.get("letra", "").upper() == "C:"), {})

        campos_info = [
            ("Sistema Operativo:", f"{sis.get('so', 'Windows')} ({sis.get('compilacion', 'N/D')})"),
            ("Arquitectura CPU:", f"{sis.get('arquitectura', 'N/D')} ({sis.get('nucleos', 1)} hilos)"),
            ("Procesador:", sis.get('cpu', 'N/D')),
            ("Usuario Actual:", f"{sis.get('usuario', 'N/D')} ({'Administrador' if sis.get('es_admin') else 'Usuario Estándar'})"),
            ("Nombre del Equipo:", sis.get('equipo', 'N/D')),
            ("Tiempo Activo (Uptime):", sis.get('uptime', 'N/D')),
        ]

        # Reacomodar con grid según modo
        cols = 2 if self.modo_responsive_actual != "compacto" else 1
        for idx, (tit, val) in enumerate(campos_info):
            r = idx if cols == 1 else idx // 2
            c = 0 if cols == 1 else (idx % 2) * 2

            tk.Label(self.f_info_grid, text=tit, font=("Segoe UI", 10, "bold"), fg=COLOR_PINK_SOFT, bg=COLOR_CARD).grid(row=r, column=c, sticky="w", pady=3)
            tk.Label(self.f_info_grid, text=val, font=("Segoe UI", 10), fg=COLOR_TEXT_MAIN, bg=COLOR_CARD).grid(row=r, column=c+1, sticky="w", padx=(6, 20), pady=3)

        # 4. Barras Visuales de Recursos (RAM y Disco C:)
        c_barras = self._crear_tarjeta(content, "BARRAS VISUALES DE CARGA DE RECURSOS", "📊")
        self.f_bar_res = tk.Frame(c_barras, bg=COLOR_CARD)
        self.f_bar_res.pack(fill=tk.X, padx=16, pady=(0, 14))

        pct_ram = ram.get("carga_pct", 50)
        tk.Label(
            self.f_bar_res,
            text=f"Memoria RAM: {ram.get('usado_gb', 0)} GB usados de {ram.get('total_gb', 0)} GB ({pct_ram}% de carga)",
            font=("Segoe UI", 10, "bold"),
            fg=COLOR_TEXT_MAIN,
            bg=COLOR_CARD
        ).pack(anchor="w", pady=(2, 2))
        self._dibujar_barra_canvas_responsive(self.f_bar_res, pct_ram)

        if disco_c:
            pct_disco = disco_c.get("pct_usado", 50)
            tk.Label(
                self.f_bar_res,
                text=f"Disco Principal C:: {disco_c.get('usado_gb', 0)} GB ocupados de {disco_c.get('total_gb', 0)} GB ({pct_disco}% de uso)",
                font=("Segoe UI", 10, "bold"),
                fg=COLOR_TEXT_MAIN,
                bg=COLOR_CARD
            ).pack(anchor="w", pady=(10, 2))
            self._dibujar_barra_canvas_responsive(self.f_bar_res, pct_disco)

        self.actualizar_estado("Información general y salud cargadas.")

    def _dibujar_barra_canvas_responsive(self, parent, porcentaje):
        """Barra de progreso Canvas que se estira al 100% del ancho disponible."""
        c = tk.Canvas(parent, height=18, bg=COLOR_SIDEBAR, highlightthickness=0)
        c.pack(fill=tk.X, expand=True, pady=2)

        def _redibujar(event):
            c.delete("all")
            w = event.width
            color = COLOR_GREEN if porcentaje < 75 else (COLOR_YELLOW if porcentaje < 88 else COLOR_PINK_INT)
            ancho_bar = max(4, int((porcentaje / 100.0) * w))
            c.create_rectangle(0, 0, ancho_bar, 18, fill=color, outline="")

        c.bind("<Configure>", _redibujar)

    # ==========================================================================
    # HERRAMIENTA 2: MONITOR DE RENDIMIENTO EN VIVO (CPU Y RAM)
    # ==========================================================================

    def _mostrar_herramienta_2(self):
        """Monitor en tiempo real de CPU y RAM con gráfico adaptable de 60 segundos."""
        self._resaltar_boton_activo("2")
        self._limpiar_panel_central()

        self.scroll_activo = scroll_box = MarcoConScroll(self.center_frame)
        scroll_box.pack(fill=tk.BOTH, expand=True)
        content = scroll_box.interior

        c_mon = self._crear_tarjeta(content, "MONITOR DE RENDIMIENTO EN TIEMPO REAL (ÚLTIMOS 60 SEGUNDOS)", "📈")
        f_m = tk.Frame(c_mon, bg=COLOR_CARD)
        f_m.pack(fill=tk.X, padx=16, pady=(0, 14))

        # Tarjetas numéricas superiores (Grid de 2 o 1 columna)
        self.f_nums_mon = tk.Frame(f_m, bg=COLOR_CARD)
        self.f_nums_mon.pack(fill=tk.X, pady=(0, 10))

        # CPU
        self.box_cpu = tk.Frame(self.f_nums_mon, bg=COLOR_SIDEBAR, padx=16, pady=10)
        self.box_cpu.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        tk.Label(self.box_cpu, text="PROCESADOR (CPU)", font=("Segoe UI", 10, "bold"), fg=COLOR_PINK_SOFT, bg=COLOR_SIDEBAR).pack(anchor="w")
        self.lbl_cpu_num = tk.Label(self.box_cpu, text="0.0%", font=("Segoe UI", 26, "bold"), fg=COLOR_TEXT_MAIN, bg=COLOR_SIDEBAR)
        self.lbl_cpu_num.pack(anchor="w")
        self.lbl_cpu_frase = tk.Label(self.box_cpu, text="Calculando...", font=("Segoe UI", 10), fg=COLOR_TEXT_MUTED, bg=COLOR_SIDEBAR)
        self.lbl_cpu_frase.pack(anchor="w")

        # RAM
        self.box_ram = tk.Frame(self.f_nums_mon, bg=COLOR_SIDEBAR, padx=16, pady=10)
        self.box_ram.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(6, 0))

        tk.Label(self.box_ram, text="MEMORIA FÍSICA (RAM)", font=("Segoe UI", 10, "bold"), fg=COLOR_PURPLE_LGT, bg=COLOR_SIDEBAR).pack(anchor="w")
        self.lbl_ram_num = tk.Label(self.box_ram, text="0.0%", font=("Segoe UI", 26, "bold"), fg=COLOR_TEXT_MAIN, bg=COLOR_SIDEBAR)
        self.lbl_ram_num.pack(anchor="w")
        self.lbl_ram_frase = tk.Label(self.box_ram, text="Calculando...", font=("Segoe UI", 10), fg=COLOR_TEXT_MUTED, bg=COLOR_SIDEBAR)
        self.lbl_ram_frase.pack(anchor="w")

        # Gráfico Canvas que llena todo el ancho disponible
        self.canvas_monitor = tk.Canvas(f_m, height=200, bg=COLOR_SIDEBAR, highlightthickness=1, highlightbackground=COLOR_BORDER)
        self.canvas_monitor.pack(fill=tk.X, expand=True, pady=6)
        self.canvas_monitor.bind("<Configure>", lambda e: self._dibujar_grafico_rendimiento())

        # Controles
        f_ctrl = tk.Frame(f_m, bg=COLOR_CARD)
        f_ctrl.pack(fill=tk.X, pady=(10, 0))

        self.btn_pausar = tk.Button(
            f_ctrl,
            text="⏸ Pausar Monitor",
            font=("Segoe UI", 10, "bold"),
            bg=COLOR_PURPLE_MAIN,
            fg="#FFFFFF",
            bd=0,
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._alternar_pausa_monitor
        )
        self.btn_pausar.pack(side=tk.LEFT)

        tk.Label(
            f_ctrl,
            text="Leyenda:  — CPU (Rosado)   — RAM (Morado Claro)",
            font=("Segoe UI", 10),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_CARD
        ).pack(side=tk.RIGHT)

        # Iniciar ciclo de actualización
        self.monitor_activo = True
        self.monitor_pausado = False
        self._ciclo_actualizar_monitor()

    def _alternar_pausa_monitor(self):
        self.monitor_pausado = not self.monitor_pausado
        if self.monitor_pausado:
            self.btn_pausar.config(text="▶ Reanudar Monitor", bg=COLOR_GREEN, fg="#1A0B2E")
            self.actualizar_estado("Monitor de rendimiento pausado.")
        else:
            self.btn_pausar.config(text="⏸ Pausar Monitor", bg=COLOR_PURPLE_MAIN, fg="#FFFFFF")
            self.actualizar_estado("Monitor de rendimiento reanudado.")

    def _ciclo_actualizar_monitor(self):
        if not self.monitor_activo:
            return

        if not self.monitor_pausado:
            datos = logica.medir_rendimiento_en_vivo()
            self.datos_sesion["rendimiento"] = datos

            cpu_val = datos["cpu_pct"]
            ram_val = datos["ram_pct"]

            self.historial_cpu.pop(0)
            self.historial_cpu.append(cpu_val)
            self.historial_ram.pop(0)
            self.historial_ram.append(ram_val)

            color_cpu = COLOR_PINK_INT if cpu_val > 80.0 else COLOR_TEXT_MAIN
            color_ram = COLOR_PINK_INT if ram_val > 80.0 else COLOR_TEXT_MAIN

            self.lbl_cpu_num.config(text=f"{cpu_val:.1f}%", fg=color_cpu)
            self.lbl_cpu_frase.config(text=datos["frase_cpu"])

            self.lbl_ram_num.config(text=f"{ram_val:.1f}% ({datos['ram_usada_gb']:.1f} / {datos['ram_total_gb']:.1f} GB)", fg=color_ram)
            self.lbl_ram_frase.config(text=datos["frase_ram"])

            self._dibujar_grafico_rendimiento()

        self.despacho_monitor_id = self.after(1000, self._ciclo_actualizar_monitor)

    def _dibujar_grafico_rendimiento(self):
        """Renderiza las curvas de CPU y RAM con coordenadas proporcionales al tamaño real del Canvas."""
        c = self.canvas_monitor
        c.delete("all")
        w = max(200, c.winfo_width())
        h = max(100, c.winfo_height())

        pad_x = 42
        pad_y = 15
        grafico_w = max(50, w - pad_x - 12)
        grafico_h = max(30, h - (pad_y * 2))

        # Líneas horizontales de cuadrícula (0%, 50%, 100%)
        for pct, y_rel in [(100, pad_y), (50, pad_y + grafico_h // 2), (0, pad_y + grafico_h)]:
            c.create_line(pad_x, y_rel, w - 10, y_rel, fill="#3E1E6B", dash=(2, 2))
            c.create_text(pad_x - 6, y_rel, text=f"{pct}%", fill=COLOR_TEXT_MUTED, font=("Segoe UI", 8), anchor="e")

        paso_x = grafico_w / 59.0
        puntos_cpu = []
        puntos_ram = []

        for i in range(60):
            x = pad_x + (i * paso_x)
            val_c = self.historial_cpu[i]
            val_r = self.historial_ram[i]

            y_c = (pad_y + grafico_h) - ((val_c / 100.0) * grafico_h)
            y_r = (pad_y + grafico_h) - ((val_r / 100.0) * grafico_h)

            puntos_cpu.extend([x, y_c])
            puntos_ram.extend([x, y_r])

        col_c = COLOR_PINK_INT if self.historial_cpu[-1] > 80 else COLOR_PINK_SOFT
        col_r = COLOR_PINK_INT if self.historial_ram[-1] > 80 else COLOR_PURPLE_LGT

        if len(puntos_ram) >= 4:
            c.create_line(puntos_ram, fill=col_r, width=2, smooth=True)
        if len(puntos_cpu) >= 4:
            c.create_line(puntos_cpu, fill=col_c, width=2, smooth=True)

    # ==========================================================================
    # HERRAMIENTA 3: DISCOS Y ARCHIVOS
    # ==========================================================================

    def _mostrar_herramienta_3(self):
        """Discos, explorador de archivos responsive y buscador de los 20 más pesados."""
        self._resaltar_boton_activo("3")
        self._limpiar_panel_central()

        self.scroll_activo = scroll_box = MarcoConScroll(self.center_frame)
        scroll_box.pack(fill=tk.BOTH, expand=True)
        content = scroll_box.interior

        # 1. Unidades de disco
        c_disc = self._crear_tarjeta(content, "UNIDADES DE DISCO Y PARTICIONES", "💽")
        f_d = tk.Frame(c_disc, bg=COLOR_CARD)
        f_d.pack(fill=tk.X, padx=16, pady=(0, 14))

        discos = logica.accion_espacio_disco()
        self.datos_sesion["discos"] = discos

        for d in discos:
            f_u = tk.Frame(f_d, bg=COLOR_CARD)
            f_u.pack(fill=tk.X, pady=4)

            tk.Label(
                f_u,
                text=f"Unidad {d['letra']} (Total: {d['total_gb']} GB | Usado: {d['usado_gb']} GB | Libre: {d['libre_gb']} GB - {d['pct_libre']}% libre)",
                font=("Segoe UI", 10, "bold"),
                fg=COLOR_TEXT_MAIN,
                bg=COLOR_CARD
            ).pack(anchor="w")

            self._dibujar_barra_canvas_responsive(f_u, d["pct_usado"])

        # 2. Administrador de Archivos Responsive
        c_expl = self._crear_tarjeta(content, "ADMINISTRADOR DE ARCHIVOS", "📁")
        f_e = tk.Frame(c_expl, bg=COLOR_CARD)
        f_e.pack(fill=tk.X, padx=16, pady=(0, 14))

        f_nav = tk.Frame(f_e, bg=COLOR_CARD)
        f_nav.pack(fill=tk.X, pady=(0, 8))

        tk.Label(f_nav, text="Ruta:", font=("Segoe UI", 10, "bold"), fg=COLOR_PINK_SOFT, bg=COLOR_CARD).pack(side=tk.LEFT)

        self.var_ruta_explorador = tk.StringVar(value=str(Path.home()))
        ent_ruta = tk.Entry(f_nav, textvariable=self.var_ruta_explorador, font=("Segoe UI", 10), bg=COLOR_SIDEBAR, fg=COLOR_TEXT_MAIN, bd=0)
        ent_ruta.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)

        tk.Button(
            f_nav,
            text="⬆ Subir",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_SIDEBAR,
            fg=COLOR_TEXT_MAIN,
            bd=0,
            padx=8,
            pady=3,
            cursor="hand2",
            command=self._explorador_subir_nivel
        ).pack(side=tk.LEFT, padx=2)

        tk.Button(
            f_nav,
            text="📂 Elegir",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_PURPLE_MAIN,
            fg="#FFFFFF",
            bd=0,
            padx=8,
            pady=3,
            cursor="hand2",
            command=self._explorador_elegir_carpeta
        ).pack(side=tk.LEFT, padx=2)

        # Treeview con scroll vertical y horizontal
        f_tree_e = tk.Frame(f_e, bg=COLOR_CARD)
        f_tree_e.pack(fill=tk.BOTH, expand=True)

        cols_e = ("nombre", "tipo", "tamano", "fecha")
        self.tree_explorador = ttk.Treeview(f_tree_e, columns=cols_e, show="headings", height=7)
        self.tree_explorador.heading("nombre", text="Nombre")
        self.tree_explorador.heading("tipo", text="Tipo")
        self.tree_explorador.heading("tamano", text="Tamaño")
        self.tree_explorador.heading("fecha", text="Modificación")

        self.tree_explorador.column("nombre", width=260, minwidth=120, stretch=True)
        self.tree_explorador.column("tipo", width=110, minwidth=80, stretch=True)
        self.tree_explorador.column("tamano", width=90, minwidth=60, stretch=True)
        self.tree_explorador.column("fecha", width=130, minwidth=100, stretch=True)

        scroll_y_e = ttk.Scrollbar(f_tree_e, orient="vertical", command=self.tree_explorador.yview, style="Vertical.TScrollbar")
        scroll_x_e = ttk.Scrollbar(f_tree_e, orient="horizontal", command=self.tree_explorador.xview, style="Horizontal.TScrollbar")
        self.tree_explorador.configure(yscrollcommand=scroll_y_e.set, xscrollcommand=scroll_x_e.set)

        self.tree_explorador.grid(row=0, column=0, sticky="nsew")
        scroll_y_e.grid(row=0, column=1, sticky="ns")
        scroll_x_e.grid(row=1, column=0, sticky="ew")

        f_tree_e.grid_rowconfigure(0, weight=1)
        f_tree_e.grid_columnconfigure(0, weight=1)

        self.tree_explorador.bind("<Double-1>", self._explorador_doble_clic)

        # Botones de acción del explorador
        f_act = tk.Frame(f_e, bg=COLOR_CARD)
        f_act.pack(fill=tk.X, pady=(8, 0))

        acciones_e = [
            ("Abrir", self._explorador_abrir),
            ("Renombrar", self._explorador_renombrar),
            ("Nueva carpeta", self._explorador_nueva_carpeta),
            ("Copiar ruta", self._explorador_copiar_ruta),
            ("Eliminar", self._explorador_eliminar),
        ]

        for txt, cmd in acciones_e:
            tk.Button(
                f_act,
                text=txt,
                font=("Segoe UI", 9, "bold"),
                bg=COLOR_SIDEBAR,
                fg=COLOR_TEXT_MAIN,
                bd=0,
                padx=8,
                pady=4,
                cursor="hand2",
                command=cmd
            ).pack(side=tk.LEFT, padx=2)

        self._explorador_refrescar()

        # 3. Top 20 archivos más pesados
        c_pes = self._crear_tarjeta(content, "BÚSQUEDA DE ARCHIVOS MÁS PESADOS (TOP 20)", "🔍")
        f_p = tk.Frame(c_pes, bg=COLOR_CARD)
        f_p.pack(fill=tk.X, padx=16, pady=(0, 14))

        f_ctrl_p = tk.Frame(f_p, bg=COLOR_CARD)
        f_ctrl_p.pack(fill=tk.X, pady=(0, 8))

        self.btn_buscar_pesados = tk.Button(
            f_ctrl_p,
            text="🔍 Buscar archivos más pesados",
            font=("Segoe UI", 10, "bold"),
            bg=COLOR_PINK_INT,
            fg="#FFFFFF",
            bd=0,
            padx=12,
            pady=4,
            cursor="hand2",
            command=self._iniciar_busqueda_pesados
        )
        self.btn_buscar_pesados.pack(side=tk.LEFT)

        self.btn_cancelar_pesados = tk.Button(
            f_ctrl_p,
            text="Cancelar",
            font=("Segoe UI", 10),
            bg=COLOR_SIDEBAR,
            fg=COLOR_TEXT_MUTED,
            bd=0,
            padx=10,
            pady=4,
            state="disabled",
            command=self._cancelar_busqueda_pesados
        )
        self.btn_cancelar_pesados.pack(side=tk.LEFT, padx=6)

        self.lbl_estado_pesados = tk.Label(f_ctrl_p, text="Escanea la carpeta actual.", font=("Segoe UI", 10), fg=COLOR_TEXT_MUTED, bg=COLOR_CARD)
        self.lbl_estado_pesados.pack(side=tk.LEFT, padx=6)

        f_tree_p = tk.Frame(f_p, bg=COLOR_CARD)
        f_tree_p.pack(fill=tk.BOTH, expand=True)

        cols_p = ("pos", "nombre", "tamano", "carpeta", "fecha")
        self.tree_pesados = ttk.Treeview(f_tree_p, columns=cols_p, show="headings", height=6)
        self.tree_pesados.heading("pos", text="#")
        self.tree_pesados.heading("nombre", text="Archivo")
        self.tree_pesados.heading("tamano", text="Tamaño")
        self.tree_pesados.heading("carpeta", text="Carpeta contenedora")
        self.tree_pesados.heading("fecha", text="Fecha")

        self.tree_pesados.column("pos", width=35, minwidth=30, anchor="center")
        self.tree_pesados.column("nombre", width=180, minwidth=100, stretch=True)
        self.tree_pesados.column("tamano", width=95, minwidth=70, stretch=True)
        self.tree_pesados.column("carpeta", width=220, minwidth=120, stretch=True)
        self.tree_pesados.column("fecha", width=120, minwidth=90, stretch=True)

        scroll_y_p = ttk.Scrollbar(f_tree_p, orient="vertical", command=self.tree_pesados.yview, style="Vertical.TScrollbar")
        scroll_x_p = ttk.Scrollbar(f_tree_p, orient="horizontal", command=self.tree_pesados.xview, style="Horizontal.TScrollbar")
        self.tree_pesados.configure(yscrollcommand=scroll_y_p.set, xscrollcommand=scroll_x_p.set)

        self.tree_pesados.grid(row=0, column=0, sticky="nsew")
        scroll_y_p.grid(row=0, column=1, sticky="ns")
        scroll_x_p.grid(row=1, column=0, sticky="ew")

        f_tree_p.grid_rowconfigure(0, weight=1)
        f_tree_p.grid_columnconfigure(0, weight=1)

        f_act_p = tk.Frame(f_p, bg=COLOR_CARD)
        f_act_p.pack(fill=tk.X, pady=(8, 0))

        tk.Button(f_act_p, text="Abrir carpeta contenedora", font=("Segoe UI", 9, "bold"), bg=COLOR_SIDEBAR, fg=COLOR_TEXT_MAIN, bd=0, padx=8, pady=4, cursor="hand2", command=self._pesados_abrir_carpeta).pack(side=tk.LEFT, padx=2)
        tk.Button(f_act_p, text="Eliminar archivo pesado", font=("Segoe UI", 9, "bold"), bg=COLOR_SIDEBAR, fg=COLOR_RED, bd=0, padx=8, pady=4, cursor="hand2", command=self._pesados_eliminar).pack(side=tk.LEFT, padx=2)

    # Explorador Handlers
    def _explorador_refrescar(self):
        ruta = Path(self.var_ruta_explorador.get())
        for row in self.tree_explorador.get_children():
            self.tree_explorador.delete(row)

        items = logica.explorador_listar_directorio(ruta)
        for nombre, tipo, tam_str, mtime, es_dir, obj_ruta in items:
            self.tree_explorador.insert("", "end", values=(nombre, tipo, tam_str, mtime), tags=(str(obj_ruta),))

    def _explorador_subir_nivel(self):
        actual = Path(self.var_ruta_explorador.get())
        padre = actual.parent
        if padre.exists():
            self.var_ruta_explorador.set(str(padre))
            self._explorador_refrescar()

    def _explorador_elegir_carpeta(self):
        sel = filedialog.askdirectory(initialdir=self.var_ruta_explorador.get())
        if sel:
            self.var_ruta_explorador.set(sel)
            self._explorador_refrescar()

    def _explorador_doble_clic(self, event):
        item = self.tree_explorador.selection()
        if not item:
            return
        tags = self.tree_explorador.item(item[0], "tags")
        if tags:
            ruta = Path(tags[0])
            if ruta.is_dir():
                self.var_ruta_explorador.set(str(ruta))
                self._explorador_refrescar()

    def _obtener_item_seleccionado_explorador(self) -> Path:
        item = self.tree_explorador.selection()
        if not item:
            messagebox.showinfo("Selección", "Selecciona un archivo o carpeta.", parent=self)
            return None
        tags = self.tree_explorador.item(item[0], "tags")
        return Path(tags[0]) if tags else None

    def _explorador_abrir(self):
        sel = self._obtener_item_seleccionado_explorador()
        if sel and sel.exists():
            try:
                os.startfile(str(sel))
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self)

    def _explorador_renombrar(self):
        sel = self._obtener_item_seleccionado_explorador()
        if not sel:
            return
        nuevo = simpledialog.askstring("Renombrar", f"Nuevo nombre para '{sel.name}':", initialvalue=sel.name, parent=self)
        if nuevo and nuevo.strip() != sel.name:
            res = logica.explorador_renombrar(sel, nuevo)
            if res["ok"]:
                self._explorador_refrescar()
            else:
                messagebox.showerror("Error", res["mensaje"], parent=self)

    def _explorador_nueva_carpeta(self):
        ruta_act = Path(self.var_ruta_explorador.get())
        nombre = simpledialog.askstring("Nueva Carpeta", "Escribe el nombre de la carpeta:", parent=self)
        if nombre:
            res = logica.explorador_crear_carpeta(ruta_act, nombre)
            if res["ok"]:
                self._explorador_refrescar()
            else:
                messagebox.showerror("Error", res["mensaje"], parent=self)

    def _explorador_copiar_ruta(self):
        sel = self._obtener_item_seleccionado_explorador()
        if sel:
            self.clipboard_clear()
            self.clipboard_append(str(sel.resolve()))
            self.actualizar_estado("Ruta copiada.")

    def _explorador_eliminar(self):
        sel = self._obtener_item_seleccionado_explorador()
        if not sel:
            return
        if not messagebox.askyesno("Confirmar", f"¿Eliminar permanentemente:\n{sel.name}?", parent=self):
            return
        res = logica.explorador_eliminar(sel)
        if res["ok"]:
            self._explorador_refrescar()
            self.actualizar_estado(res["mensaje"])
        else:
            messagebox.showwarning("Restricción", res["mensaje"], parent=self)

    # Top Pesados Handlers
    def _iniciar_busqueda_pesados(self):
        carpeta = Path(self.var_ruta_explorador.get())
        self.btn_buscar_pesados.config(state="disabled")
        self.btn_cancelar_pesados.config(state="normal")
        self.lbl_estado_pesados.config(text=f"Escaneando en {carpeta.name}...")

        self.cancel_event_pesados = threading.Event()
        for row in self.tree_pesados.get_children():
            self.tree_pesados.delete(row)

        def worker():
            top = logica.buscar_archivos_mas_pesados(
                carpeta,
                cancel_event=self.cancel_event_pesados,
                progress_callback=lambda n: self.despachar_hilo_principal(lambda: self.actualizar_estado(f"Archivos analizados: {n}"))
            )
            self.despachar_hilo_principal(lambda: self._finalizar_busqueda_pesados(top))

        threading.Thread(target=worker, daemon=True).start()

    def _cancelar_busqueda_pesados(self):
        if self.cancel_event_pesados:
            self.cancel_event_pesados.set()
            self.lbl_estado_pesados.config(text="Búsqueda cancelada.")
            self.btn_cancelar_pesados.config(state="disabled")

    def _finalizar_busqueda_pesados(self, top_archivos):
        self.btn_buscar_pesados.config(state="normal")
        self.btn_cancelar_pesados.config(state="disabled")
        self.datos_sesion["archivos_pesados"] = top_archivos

        for i, item in enumerate(top_archivos, 1):
            self.tree_pesados.insert(
                "", "end",
                values=(i, item["nombre"], item["tam_legible"], item["carpeta"], item["fecha"]),
                tags=(str(item["ruta_completa"]),)
            )

        self.lbl_estado_pesados.config(text=f"Top {len(top_archivos)} encontrados.")
        self.actualizar_estado("Escaneo completado.", 100)

    def _pesados_abrir_carpeta(self):
        item = self.tree_pesados.selection()
        if not item:
            messagebox.showinfo("Selección", "Selecciona un archivo.", parent=self)
            return
        tags = self.tree_pesados.item(item[0], "tags")
        if tags:
            ruta_f = Path(tags[0])
            if ruta_f.exists():
                subprocess.run(["explorer", f"/select,{ruta_f}"], creationflags=logica.NO_WINDOW)

    def _pesados_eliminar(self):
        item = self.tree_pesados.selection()
        if not item:
            return
        tags = self.tree_pesados.item(item[0], "tags")
        if not tags:
            return
        ruta_f = Path(tags[0])
        if not messagebox.askyesno("Eliminar", f"¿Eliminar archivo pesado?\n{ruta_f.name}", parent=self):
            return
        res = logica.explorador_eliminar(ruta_f)
        if res["ok"]:
            self.tree_pesados.delete(item[0])
            self.actualizar_estado(res["mensaje"])
        else:
            messagebox.showwarning("Aviso", res["mensaje"], parent=self)

    # ==========================================================================
    # HERRAMIENTA 4: PROGRAMAS Y ERRORES DEL SISTEMA
    # ==========================================================================

    def _mostrar_herramienta_4(self):
        """Pestañas Notebook que se expanden proporcionalmente."""
        self._resaltar_boton_activo("4")
        self._limpiar_panel_central()

        self.scroll_activo = scroll_box = MarcoConScroll(self.center_frame)
        scroll_box.pack(fill=tk.BOTH, expand=True)
        content = scroll_box.interior

        c_padre = self._crear_tarjeta(content, "ADMINISTRACIÓN DE SOFTWARE Y AUDITORÍA DE EVENTOS", "⚙")
        f_p = tk.Frame(c_padre, bg=COLOR_CARD)
        f_p.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 14))

        notebook = ttk.Notebook(f_p)
        notebook.pack(fill=tk.BOTH, expand=True, pady=6)
        notebook.bind("<<NotebookTabChanged>>", lambda e: scroll_box._actualizar_geometria())

        # TAB 1: Instalados
        tab_inst = tk.Frame(notebook, bg=COLOR_CARD, padx=8, pady=8)
        notebook.add(tab_inst, text="📦 Programas Instalados")

        f_busq = tk.Frame(tab_inst, bg=COLOR_CARD)
        f_busq.pack(fill=tk.X, pady=(0, 8))

        tk.Label(f_busq, text="Buscar:", font=("Segoe UI", 10, "bold"), fg=COLOR_PINK_SOFT, bg=COLOR_CARD).pack(side=tk.LEFT)
        self.var_filtro_prog = tk.StringVar()
        ent_busq = tk.Entry(f_busq, textvariable=self.var_filtro_prog, font=("Segoe UI", 10), bg=COLOR_SIDEBAR, fg=COLOR_TEXT_MAIN, bd=0)
        ent_busq.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
        self.var_filtro_prog.trace_add("write", lambda *args: self._filtrar_programas_instalados())

        self.lbl_cont_prog = tk.Label(f_busq, text="Total: 0", font=("Segoe UI", 10, "bold"), fg=COLOR_TEXT_MUTED, bg=COLOR_CARD)
        self.lbl_cont_prog.pack(side=tk.RIGHT)

        f_tree_i = tk.Frame(tab_inst, bg=COLOR_CARD)
        f_tree_i.pack(fill=tk.BOTH, expand=True)

        cols_i = ("nombre", "version", "editor", "fecha", "tamano")
        self.tree_programas = ttk.Treeview(f_tree_i, columns=cols_i, show="headings", height=8)
        self.tree_programas.heading("nombre", text="Nombre del Programa")
        self.tree_programas.heading("version", text="Versión")
        self.tree_programas.heading("editor", text="Editor")
        self.tree_programas.heading("fecha", text="Instalado")
        self.tree_programas.heading("tamano", text="Tamaño Est.")

        self.tree_programas.column("nombre", width=220, minwidth=120, stretch=True)
        self.tree_programas.column("version", width=90, minwidth=60, stretch=True)
        self.tree_programas.column("editor", width=160, minwidth=100, stretch=True)
        self.tree_programas.column("fecha", width=90, minwidth=60, stretch=True)
        self.tree_programas.column("tamano", width=80, minwidth=60, stretch=True)

        sy_i = ttk.Scrollbar(f_tree_i, orient="vertical", command=self.tree_programas.yview, style="Vertical.TScrollbar")
        sx_i = ttk.Scrollbar(f_tree_i, orient="horizontal", command=self.tree_programas.xview, style="Horizontal.TScrollbar")
        self.tree_programas.configure(yscrollcommand=sy_i.set, xscrollcommand=sx_i.set)

        self.tree_programas.grid(row=0, column=0, sticky="nsew")
        sy_i.grid(row=0, column=1, sticky="ns")
        sx_i.grid(row=1, column=0, sticky="ew")

        f_tree_i.grid_rowconfigure(0, weight=1)
        f_tree_i.grid_columnconfigure(0, weight=1)

        # TAB 2: Inicio
        tab_ini = tk.Frame(notebook, bg=COLOR_CARD, padx=8, pady=8)
        notebook.add(tab_ini, text="🚀 Programas de Inicio")

        f_tree_ini = tk.Frame(tab_ini, bg=COLOR_CARD)
        f_tree_ini.pack(fill=tk.BOTH, expand=True)

        cols_ini = ("nombre", "origen", "comando")
        self.tree_inicio = ttk.Treeview(f_tree_ini, columns=cols_ini, show="headings", height=8)
        self.tree_inicio.heading("nombre", text="Nombre")
        self.tree_inicio.heading("origen", text="Origen")
        self.tree_inicio.heading("comando", text="Comando de Ejecución")

        self.tree_inicio.column("nombre", width=140, minwidth=100, stretch=True)
        self.tree_inicio.column("origen", width=170, minwidth=110, stretch=True)
        self.tree_inicio.column("comando", width=320, minwidth=180, stretch=True)

        sy_ini = ttk.Scrollbar(f_tree_ini, orient="vertical", command=self.tree_inicio.yview, style="Vertical.TScrollbar")
        sx_ini = ttk.Scrollbar(f_tree_ini, orient="horizontal", command=self.tree_inicio.xview, style="Horizontal.TScrollbar")
        self.tree_inicio.configure(yscrollcommand=sy_ini.set, xscrollcommand=sx_ini.set)

        self.tree_inicio.grid(row=0, column=0, sticky="nsew")
        sy_ini.grid(row=0, column=1, sticky="ns")
        sx_ini.grid(row=1, column=0, sticky="ew")

        f_tree_ini.grid_rowconfigure(0, weight=1)
        f_tree_ini.grid_columnconfigure(0, weight=1)

        # TAB 3: Errores
        tab_err = tk.Frame(notebook, bg=COLOR_CARD, padx=8, pady=8)
        notebook.add(tab_err, text="⚠️ Errores Recientes")

        self.f_aviso_err = tk.Frame(tab_err, bg=COLOR_SIDEBAR, padx=12, pady=8)
        self.f_aviso_err.pack(fill=tk.X, pady=(0, 6))

        self.lbl_aviso_err_tit = tk.Label(self.f_aviso_err, text="Visor de Eventos del Sistema", font=("Segoe UI", 10, "bold"), fg=COLOR_PINK_SOFT, bg=COLOR_SIDEBAR)
        self.lbl_aviso_err_tit.pack(anchor="w")
        self.lbl_aviso_err_desc = tk.Label(self.f_aviso_err, text="Consultando eventos...", font=("Segoe UI", 10), fg=COLOR_TEXT_MAIN, bg=COLOR_SIDEBAR, justify="left", wraplength=700)
        self.lbl_aviso_err_desc.pack(anchor="w", pady=(2, 0))

        f_tree_err = tk.Frame(tab_err, bg=COLOR_CARD)
        f_tree_err.pack(fill=tk.BOTH, expand=True)

        cols_err = ("fecha", "origen", "id", "nivel", "mensaje")
        self.tree_errores = ttk.Treeview(f_tree_err, columns=cols_err, show="headings", height=7)
        self.tree_errores.heading("fecha", text="Fecha / Hora")
        self.tree_errores.heading("origen", text="Origen")
        self.tree_errores.heading("id", text="ID")
        self.tree_errores.heading("nivel", text="Nivel")
        self.tree_errores.heading("mensaje", text="Mensaje Resumido")

        self.tree_errores.column("fecha", width=120, minwidth=90, stretch=True)
        self.tree_errores.column("origen", width=130, minwidth=90, stretch=True)
        self.tree_errores.column("id", width=60, minwidth=40, anchor="center")
        self.tree_errores.column("nivel", width=80, minwidth=60, anchor="center")
        self.tree_errores.column("mensaje", width=260, minwidth=140, stretch=True)

        sy_err = ttk.Scrollbar(f_tree_err, orient="vertical", command=self.tree_errores.yview, style="Vertical.TScrollbar")
        sx_err = ttk.Scrollbar(f_tree_err, orient="horizontal", command=self.tree_errores.xview, style="Horizontal.TScrollbar")
        self.tree_errores.configure(yscrollcommand=sy_err.set, xscrollcommand=sx_err.set)

        self.tree_errores.grid(row=0, column=0, sticky="nsew")
        sy_err.grid(row=0, column=1, sticky="ns")
        sx_err.grid(row=1, column=0, sticky="ew")

        f_tree_err.grid_rowconfigure(0, weight=1)
        f_tree_err.grid_columnconfigure(0, weight=1)

        self._cargar_datos_herramienta_4()

    def _cargar_datos_herramienta_4(self):
        def worker():
            progs = logica.obtener_programas_instalados()
            inis = logica.obtener_programas_inicio()
            errs = logica.obtener_errores_recientes_sistema()
            self.despachar_hilo_principal(lambda: self._mostrar_resultados_herramienta_4(progs, inis, errs))

        threading.Thread(target=worker, daemon=True).start()

    def _mostrar_resultados_herramienta_4(self, progs, inis, errs):
        self.datos_sesion["programas"] = progs
        self.datos_sesion["inicio"] = inis
        self.datos_sesion["errores"] = errs

        self._filtrar_programas_instalados()

        for item in inis:
            self.tree_inicio.insert("", "end", values=(item["nombre"], item["origen"], item["comando"]))

        if errs["ok"]:
            self.lbl_aviso_err_tit.config(text="Eventos del Sistema Registrados", fg=COLOR_GREEN)
            self.lbl_aviso_err_desc.config(
                text=f"{errs['mensaje']} Resumen: {errs['resumen_gravedad']['Critico']} Críticos | {errs['resumen_gravedad']['Error']} Errores | {errs['resumen_gravedad']['Advertencia']} Advertencias."
            )
            for ev in errs["eventos"]:
                self.tree_errores.insert("", "end", values=(ev["fecha"], ev["origen"], ev["id"], ev["nivel"], ev["mensaje"]))
        else:
            self.lbl_aviso_err_tit.config(text="Acceso Restringido por el Sistema Operativo", fg=COLOR_YELLOW)
            self.lbl_aviso_err_desc.config(
                text=f"{errs['mensaje']}\nCausa probable: {errs['causa_probable']}\nNiveles: Crítico (fallo de servicio), Error (operación fallida), Advertencia (recurso cercano al límite)."
            )

        self.actualizar_estado("Programas y eventos cargados.", 100)

    def _filtrar_programas_instalados(self):
        filtro = self.var_filtro_prog.get().lower().strip()
        progs = self.datos_sesion.get("programas") or []

        for row in self.tree_programas.get_children():
            self.tree_programas.delete(row)

        mostrados = 0
        for p in progs:
            if not filtro or filtro in p["nombre"].lower() or filtro in p["editor"].lower():
                self.tree_programas.insert("", "end", values=(p["nombre"], p["version"], p["editor"], p["fecha"], p["tamano"]))
                mostrados += 1

        self.lbl_cont_prog.config(text=f"Total: {mostrados} de {len(progs)}")

    # ==========================================================================
    # HERRAMIENTA 5: CONFIGURACIÓN IP
    # ==========================================================================

    def _mostrar_herramienta_5(self):
        """Adaptadores de red IPv4 y tabla responsive con scroll horizontal/vertical."""
        self._resaltar_boton_activo("5")
        self._limpiar_panel_central()

        self.scroll_activo = scroll_box = MarcoConScroll(self.center_frame)
        scroll_box.pack(fill=tk.BOTH, expand=True)
        content = scroll_box.interior

        c_ip = self._crear_tarjeta(content, "CONFIGURACIÓN DE RED E INTERFACES IPV4", "🌐")
        f_ip = tk.Frame(c_ip, bg=COLOR_CARD)
        f_ip.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 14))

        tk.Label(
            f_ip,
            text=f"Nombre del Host en la Red: {socket.gethostname()}",
            font=("Segoe UI", 10, "bold"),
            fg=COLOR_PINK_SOFT,
            bg=COLOR_CARD
        ).pack(anchor="w", pady=(0, 8))

        f_tree_ip = tk.Frame(f_ip, bg=COLOR_CARD)
        f_tree_ip.pack(fill=tk.BOTH, expand=True)

        cols_ip = ("nombre", "ipv4", "mascara", "gateway", "mac", "dhcp")
        tree_ip = ttk.Treeview(f_tree_ip, columns=cols_ip, show="headings", height=6)
        tree_ip.heading("nombre", text="Adaptador de Red")
        tree_ip.heading("ipv4", text="Dirección IPv4")
        tree_ip.heading("mascara", text="Máscara")
        tree_ip.heading("gateway", text="Puerta de Enlace")
        tree_ip.heading("mac", text="Dirección MAC")
        tree_ip.heading("dhcp", text="DHCP")

        tree_ip.column("nombre", width=200, minwidth=130, stretch=True)
        tree_ip.column("ipv4", width=110, minwidth=90, stretch=True)
        tree_ip.column("mascara", width=110, minwidth=90, stretch=True)
        tree_ip.column("gateway", width=110, minwidth=90, stretch=True)
        tree_ip.column("mac", width=120, minwidth=100, stretch=True)
        tree_ip.column("dhcp", width=50, minwidth=40, anchor="center")

        sy_ip = ttk.Scrollbar(f_tree_ip, orient="vertical", command=tree_ip.yview, style="Vertical.TScrollbar")
        sx_ip = ttk.Scrollbar(f_tree_ip, orient="horizontal", command=tree_ip.xview, style="Horizontal.TScrollbar")
        tree_ip.configure(yscrollcommand=sy_ip.set, xscrollcommand=sx_ip.set)

        tree_ip.grid(row=0, column=0, sticky="nsew")
        sy_ip.grid(row=0, column=1, sticky="ns")
        sx_ip.grid(row=1, column=0, sticky="ew")

        f_tree_ip.grid_rowconfigure(0, weight=1)
        f_tree_ip.grid_columnconfigure(0, weight=1)

        datos_ip = logica.accion_configuracion_ip()
        self.datos_sesion["red"] = datos_ip

        for ad in datos_ip["adaptadores"]:
            tree_ip.insert("", "end", values=(ad["nombre"], ad["ipv4"], ad["mascara"], ad["gateway"], ad["mac"], ad["dhcp"]))

        self.actualizar_estado("Configuración IP obtenida.")

    # ==========================================================================
    # HERRAMIENTA 6: CONEXIÓN A BOSGAME
    # ==========================================================================

    def _mostrar_herramienta_6(self):
        """Formulario responsive (2 columnas en amplio/medio, 1 en compacto) y tarjeta de estadísticas."""
        self._resaltar_boton_activo("6")
        self._limpiar_panel_central()

        self.scroll_activo = scroll_box = MarcoConScroll(self.center_frame)
        scroll_box.pack(fill=tk.BOTH, expand=True)
        content = scroll_box.interior

        # 1. Formulario
        c_form = self._crear_tarjeta(content, "AUTENTICACIÓN Y CARPETA COMPARTIDA BOSGAME", "🔌")
        self.f_form_bos = tk.Frame(c_form, bg=COLOR_CARD)
        self.f_form_bos.pack(fill=tk.X, padx=16, pady=(0, 14))

        tk.Label(
            self.f_form_bos,
            text="Ingrese credenciales para conectar a la carpeta compartida en la red LAN:",
            font=("Segoe UI", 10),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_CARD
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

        # Campos
        tk.Label(self.f_form_bos, text="IP del Equipo:", font=("Segoe UI", 10, "bold"), fg=COLOR_PINK_SOFT, bg=COLOR_CARD).grid(row=1, column=0, sticky="w", pady=4)
        self.ent_bos_ip = tk.Entry(self.f_form_bos, font=("Segoe UI", 10), bg=COLOR_SIDEBAR, fg=COLOR_TEXT_MAIN, bd=0, width=22)
        self.ent_bos_ip.grid(row=1, column=1, sticky="w", padx=8, pady=4)
        self.ent_bos_ip.insert(0, logica.estado_bosgame.ip or "192.168.100.10")

        tk.Label(self.f_form_bos, text="Usuario:", font=("Segoe UI", 10, "bold"), fg=COLOR_PINK_SOFT, bg=COLOR_CARD).grid(row=2, column=0, sticky="w", pady=4)
        self.ent_bos_usr = tk.Entry(self.f_form_bos, font=("Segoe UI", 10), bg=COLOR_SIDEBAR, fg=COLOR_TEXT_MAIN, bd=0, width=22)
        self.ent_bos_usr.grid(row=2, column=1, sticky="w", padx=8, pady=4)
        self.ent_bos_usr.insert(0, logica.estado_bosgame.usuario or "")

        tk.Label(self.f_form_bos, text="Contraseña:", font=("Segoe UI", 10, "bold"), fg=COLOR_PINK_SOFT, bg=COLOR_CARD).grid(row=3, column=0, sticky="w", pady=4)
        self.ent_bos_pwd = tk.Entry(self.f_form_bos, show="•", font=("Segoe UI", 10), bg=COLOR_SIDEBAR, fg=COLOR_TEXT_MAIN, bd=0, width=22)
        self.ent_bos_pwd.grid(row=3, column=1, sticky="w", padx=8, pady=4)

        tk.Label(self.f_form_bos, text="Carpeta Compartida:", font=("Segoe UI", 10, "bold"), fg=COLOR_PINK_SOFT, bg=COLOR_CARD).grid(row=4, column=0, sticky="w", pady=4)
        self.ent_bos_share = tk.Entry(self.f_form_bos, font=("Segoe UI", 10), bg=COLOR_SIDEBAR, fg=COLOR_TEXT_MAIN, bd=0, width=22)
        self.ent_bos_share.grid(row=4, column=1, sticky="w", padx=8, pady=4)
        self.ent_bos_share.insert(0, logica.estado_bosgame.carpeta or "Compartida")

        tk.Button(
            self.f_form_bos,
            text="🔍 Buscar carpetas",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_SIDEBAR,
            fg=COLOR_TEXT_MAIN,
            bd=0,
            padx=8,
            pady=3,
            cursor="hand2",
            command=self._bosgame_buscar_shares
        ).grid(row=4, column=2, sticky="w", padx=4)

        f_btn_c = tk.Frame(self.f_form_bos, bg=COLOR_CARD)
        f_btn_c.grid(row=5, column=0, columnspan=3, sticky="w", pady=(12, 0))

        self.btn_bos_conectar = tk.Button(
            f_btn_c,
            text="⚡ Conectar a BOSGAME",
            font=("Segoe UI", 10, "bold"),
            bg=COLOR_PINK_INT,
            fg="#FFFFFF",
            bd=0,
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._bosgame_iniciar_conexion
        )
        self.btn_bos_conectar.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_bos_desconectar = tk.Button(
            f_btn_c,
            text="Desconectar",
            font=("Segoe UI", 10),
            bg=COLOR_SIDEBAR,
            fg=COLOR_TEXT_MUTED,
            bd=0,
            padx=12,
            pady=6,
            cursor="hand2",
            command=self._bosgame_desconectar
        )
        self.btn_bos_desconectar.pack(side=tk.LEFT)

        # 2. Tarjeta de Estado y Estadísticas
        c_stats = self._crear_tarjeta(content, "ESTADO DE LA CONEXIÓN Y ESTADÍSTICAS", "📊")
        self.f_bos_stats = tk.Frame(c_stats, bg=COLOR_CARD)
        self.f_bos_stats.pack(fill=tk.X, padx=16, pady=(0, 14))

        self._renderizar_tarjeta_estadisticas_bosgame()

    def _renderizar_tarjeta_estadisticas_bosgame(self):
        for w in self.f_bos_stats.winfo_children():
            w.destroy()

        st = logica.estado_bosgame
        if not st.conectado:
            tk.Label(
                self.f_bos_stats,
                text="● Estado actual: SIN CONEXIÓN",
                font=("Segoe UI", 12, "bold"),
                fg=COLOR_YELLOW,
                bg=COLOR_CARD
            ).pack(anchor="w", pady=4)
            tk.Label(
                self.f_bos_stats,
                text="Escriba la IP, usuario y contraseña arriba y presione 'Conectar a BOSGAME'.\nSe verificará la latencia, el puerto SMB (445) y se montará la ruta de red.",
                font=("Segoe UI", 10),
                fg=COLOR_TEXT_MUTED,
                bg=COLOR_CARD,
                justify="left"
            ).pack(anchor="w", pady=(2, 6))
            return

        tk.Label(
            self.f_bos_stats,
            text=f"● Estado actual: CONECTADO ({st.ruta_red})",
            font=("Segoe UI", 12, "bold"),
            fg=COLOR_GREEN,
            bg=COLOR_CARD
        ).pack(anchor="w")

        f_grid_s = tk.Frame(self.f_bos_stats, bg=COLOR_CARD)
        f_grid_s.pack(fill=tk.X, pady=8)

        items_s = [
            ("Equipo Remoto:", f"{st.ip} (Puerto 445: {'Abierto' if st.puerto_445_abierto else 'Cerrado'})"),
            ("Usuario Conectado:", st.usuario),
            ("Ruta de Red:", st.ruta_red),
            ("Calidad de Conexión:", f"{st.calidad} - {st.latencia_promedio} ms prom."),
            ("Pérdida de Paquetes:", f"{st.perdida_pct}% (Mín: {st.latencia_minima} ms / Máx: {st.latencia_maxima} ms)"),
            ("Espacio en Compartida:", f"{st.espacio_libre_gb} GB libres de {st.espacio_total_gb} GB ({st.total_archivos} archivos)"),
        ]

        cols = 2 if self.modo_responsive_actual != "compacto" else 1
        for idx, (k, v) in enumerate(items_s):
            r = idx if cols == 1 else idx // 2
            c = 0 if cols == 1 else (idx % 2) * 2
            tk.Label(f_grid_s, text=k, font=("Segoe UI", 10, "bold"), fg=COLOR_PINK_SOFT, bg=COLOR_CARD).grid(row=r, column=c, sticky="w", pady=2)
            tk.Label(f_grid_s, text=v, font=("Segoe UI", 10), fg=COLOR_TEXT_MAIN, bg=COLOR_CARD).grid(row=r, column=c+1, sticky="w", padx=(6, 16), pady=2)

        # Gráfico de Latencia Canvas
        if st.latencias:
            tk.Label(self.f_bos_stats, text="Muestras de Latencia ICMP (ms):", font=("Segoe UI", 10, "bold"), fg=COLOR_PURPLE_LGT, bg=COLOR_CARD).pack(anchor="w", pady=(8, 2))
            c_lat = tk.Canvas(self.f_bos_stats, height=60, bg=COLOR_SIDEBAR, highlightthickness=0)
            c_lat.pack(fill=tk.X, expand=True, pady=2)

            def _dibujar_lat(event):
                c_lat.delete("all")
                w = event.width
                h = event.height
                if len(st.latencias) < 2:
                    return
                max_v = max(max(st.latencias), 10.0)
                paso = w / max(1, len(st.latencias) - 1)
                pts = []
                for i, ms in enumerate(st.latencias):
                    x = i * paso
                    y = h - ((ms / max_v) * (h - 15)) - 8
                    pts.extend([x, y])
                if len(pts) >= 4:
                    c_lat.create_line(pts, fill=COLOR_PINK_SOFT, width=2, smooth=True)

            c_lat.bind("<Configure>", _dibujar_lat)

        tk.Button(
            self.f_bos_stats,
            text="🔄 Actualizar estadísticas",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_PURPLE_MAIN,
            fg="#FFFFFF",
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._bosgame_actualizar_estadisticas
        ).pack(anchor="w", pady=(10, 0))

    def _bosgame_buscar_shares(self):
        ip = self.ent_bos_ip.get().strip()
        if not logica.validar_direccion_ip(ip):
            messagebox.showwarning("IP Inválida", "Escriba una IP válida primero.", parent=self)
            return

        self.actualizar_estado(f"Consultando recursos en \\\\{ip}...")

        def worker():
            shares = logica.bosgame_listar_compartidas(ip)
            self.despachar_hilo_principal(lambda: self._mostrar_dialogo_shares(shares))

        threading.Thread(target=worker, daemon=True).start()

    def _mostrar_dialogo_shares(self, shares):
        if not shares:
            messagebox.showinfo("Carpetas", "No se detectaron carpetas públicas o SMB browsing deshabilitado.", parent=self)
            return

        # Diálogo centrado y responsive
        diag = tk.Toplevel(self)
        diag.title("Carpetas en BOSGAME")
        diag.configure(bg=COLOR_BG)
        diag.transient(self)
        diag.grab_set()

        ruta_ico = ruta_recurso("assets/icono.ico")
        if ruta_ico.exists():
            try:
                diag.iconbitmap(str(ruta_ico))
            except Exception:
                pass

        tk.Label(diag, text="Seleccione una carpeta compartida:", font=("Segoe UI", 10, "bold"), fg=COLOR_PINK_SOFT, bg=COLOR_BG).pack(pady=10)

        lista = tk.Listbox(diag, bg=COLOR_CARD, fg=COLOR_TEXT_MAIN, font=("Segoe UI", 10), bd=0, selectbackground=COLOR_PURPLE_MAIN)
        lista.pack(fill=tk.BOTH, expand=True, padx=14, pady=6)

        for s in shares:
            lista.insert("end", s)

        def elegir():
            sel = lista.curselection()
            if sel:
                self.ent_bos_share.delete(0, tk.END)
                self.ent_bos_share.insert(0, lista.get(sel[0]))
                diag.destroy()

        tk.Button(diag, text="Seleccionar", font=("Segoe UI", 10, "bold"), bg=COLOR_PINK_INT, fg="#FFFFFF", bd=0, padx=14, pady=5, command=elegir).pack(pady=10)

        # Centrar sobre la ventana principal
        self._centrar_dialogo_sobre_padre(diag, 360, 280)

    def _centrar_dialogo_sobre_padre(self, diag, ancho, alto):
        px = self.winfo_x()
        py = self.winfo_y()
        pw = self.winfo_width()
        ph = self.winfo_height()
        x = max(0, px + (pw - ancho) // 2)
        y = max(0, py + (ph - alto) // 2)
        diag.geometry(f"{ancho}x{alto}+{x}+{y}")

    def _bosgame_iniciar_conexion(self):
        ip = self.ent_bos_ip.get().strip()
        usuario = self.ent_bos_usr.get().strip()
        password = self.ent_bos_pwd.get()
        carpeta = self.ent_bos_share.get().strip()

        if not logica.validar_direccion_ip(ip):
            messagebox.showerror("Error", "Dirección IP inválida.", parent=self)
            return
        if not usuario:
            messagebox.showerror("Error", "Debe indicar el nombre de usuario.", parent=self)
            return
        if not carpeta:
            messagebox.showerror("Error", "Debe indicar la carpeta compartida.", parent=self)
            return

        self.btn_bos_conectar.config(state="disabled")
        self.actualizar_estado(f"Conectando con \\\\{ip}\\{carpeta}...", 20)

        def worker():
            res = logica.bosgame_conectar(ip, usuario, password, carpeta)
            self.despachar_hilo_principal(lambda: self._finalizar_conexion_bosgame(res))

        threading.Thread(target=worker, daemon=True).start()

    def _finalizar_conexion_bosgame(self, resultado):
        self.btn_bos_conectar.config(state="normal")
        self.actualizar_estado(resultado["mensaje"], 100)
        self._actualizar_badge_bosgame()
        self._renderizar_tarjeta_estadisticas_bosgame()

        if resultado["ok"]:
            messagebox.showinfo("Conexión Exitosa", resultado["mensaje"], parent=self)
        else:
            messagebox.showerror("Fallo de Conexión", resultado["mensaje"], parent=self)

    def _bosgame_desconectar(self):
        res = logica.bosgame_desconectar()
        self._actualizar_badge_bosgame()
        self._renderizar_tarjeta_estadisticas_bosgame()
        self.actualizar_estado(res["mensaje"])
        messagebox.showinfo("Desconexión", res["mensaje"], parent=self)

    def _bosgame_actualizar_estadisticas(self):
        self.actualizar_estado("Actualizando estadísticas...", 40)

        def worker():
            logica.bosgame_actualizar_estadisticas_almacenamiento()
            stats_lat = logica.bosgame_medir_latencias(logica.estado_bosgame.ip, cantidad=5)
            logica.estado_bosgame.latencias = stats_lat["muestras"]
            logica.estado_bosgame.latencia_promedio = stats_lat["avg"]
            logica.estado_bosgame.latencia_minima = stats_lat["min"]
            logica.estado_bosgame.latencia_maxima = stats_lat["max"]
            logica.estado_bosgame.perdida_pct = stats_lat["perdida_pct"]
            logica.estado_bosgame.calidad = stats_lat["calidad"]

            self.despachar_hilo_principal(lambda: [self._renderizar_tarjeta_estadisticas_bosgame(), self.actualizar_estado("Estadísticas actualizadas.", 100)])

        threading.Thread(target=worker, daemon=True).start()

    # ==========================================================================
    # HERRAMIENTA 7: RESPALDO DE CARPETAS (ZIP)
    # ==========================================================================

    def _mostrar_herramienta_7(self):
        """Creación de respaldos .zip y asistente de restauración."""
        self._resaltar_boton_activo("7")
        self._limpiar_panel_central()

        self.scroll_activo = scroll_box = MarcoConScroll(self.center_frame)
        scroll_box.pack(fill=tk.BOTH, expand=True)
        content = scroll_box.interior

        c_cfg = self._crear_tarjeta(content, "CREAR RESPALDO COMPRIMIDO (.ZIP)", "🗜")
        f_c = tk.Frame(c_cfg, bg=COLOR_CARD)
        f_c.pack(fill=tk.X, padx=16, pady=(0, 14))

        # Origen
        tk.Label(f_c, text="Carpeta de Origen:", font=("Segoe UI", 10, "bold"), fg=COLOR_PINK_SOFT, bg=COLOR_CARD).grid(row=0, column=0, sticky="w", pady=4)
        self.var_respaldo_origen = tk.StringVar(value=str(logica.obtener_ruta_workspace()))
        ent_origen = tk.Entry(f_c, textvariable=self.var_respaldo_origen, font=("Segoe UI", 10), bg=COLOR_SIDEBAR, fg=COLOR_TEXT_MAIN, bd=0, width=38)
        ent_origen.grid(row=0, column=1, sticky="ew", padx=8, pady=4)

        tk.Button(f_c, text="📂 Elegir origen", font=("Segoe UI", 9, "bold"), bg=COLOR_SIDEBAR, fg=COLOR_TEXT_MAIN, bd=0, padx=8, pady=3, cursor="hand2", command=self._respaldo_elegir_origen).grid(row=0, column=2, sticky="w")

        # Destino
        tk.Label(f_c, text="Destino:", font=("Segoe UI", 10, "bold"), fg=COLOR_PINK_SOFT, bg=COLOR_CARD).grid(row=1, column=0, sticky="w", pady=4)
        self.var_respaldo_dest_tipo = tk.StringVar(value="local")

        f_dest_opts = tk.Frame(f_c, bg=COLOR_CARD)
        f_dest_opts.grid(row=1, column=1, columnspan=2, sticky="w", padx=8, pady=4)

        tk.Radiobutton(f_dest_opts, text="Mi equipo", variable=self.var_respaldo_dest_tipo, value="local", font=("Segoe UI", 10), fg=COLOR_TEXT_MAIN, bg=COLOR_CARD, selectcolor=COLOR_SIDEBAR, command=self._respaldo_cambiar_tipo_destino).pack(side=tk.LEFT, padx=(0, 10))
        tk.Radiobutton(
            f_dest_opts,
            text=f"BOSGAME ({logica.estado_bosgame.ruta_red or 'Sin conexión'})",
            variable=self.var_respaldo_dest_tipo,
            value="bosgame",
            font=("Segoe UI", 10),
            fg=COLOR_TEXT_MAIN if logica.estado_bosgame.conectado else COLOR_TEXT_MUTED,
            bg=COLOR_CARD,
            selectcolor=COLOR_SIDEBAR,
            state="normal" if logica.estado_bosgame.conectado else "disabled",
            command=self._respaldo_cambiar_tipo_destino
        ).pack(side=tk.LEFT)

        # Ruta destino
        tk.Label(f_c, text="Carpeta Destino:", font=("Segoe UI", 10, "bold"), fg=COLOR_PINK_SOFT, bg=COLOR_CARD).grid(row=2, column=0, sticky="w", pady=4)
        self.var_respaldo_destino = tk.StringVar(value=str(logica.obtener_ruta_workspace()))
        self.ent_respaldo_dest = tk.Entry(f_c, textvariable=self.var_respaldo_destino, font=("Segoe UI", 10), bg=COLOR_SIDEBAR, fg=COLOR_TEXT_MAIN, bd=0, width=38)
        self.ent_respaldo_dest.grid(row=2, column=1, sticky="ew", padx=8, pady=4)

        self.btn_elegir_dest_resp = tk.Button(f_c, text="📂 Elegir destino", font=("Segoe UI", 9, "bold"), bg=COLOR_SIDEBAR, fg=COLOR_TEXT_MAIN, bd=0, padx=8, pady=3, cursor="hand2", command=self._respaldo_elegir_destino)
        self.btn_elegir_dest_resp.grid(row=2, column=2, sticky="w")

        # Nombre ZIP
        tk.Label(f_c, text="Nombre ZIP:", font=("Segoe UI", 10, "bold"), fg=COLOR_PINK_SOFT, bg=COLOR_CARD).grid(row=3, column=0, sticky="w", pady=4)
        nom_sug = logica.sugerir_nombre_respaldo(Path(self.var_respaldo_origen.get()))
        self.var_respaldo_nombre = tk.StringVar(value=nom_sug)
        ent_nombre_zip = tk.Entry(f_c, textvariable=self.var_respaldo_nombre, font=("Segoe UI", 10), bg=COLOR_SIDEBAR, fg=COLOR_TEXT_MAIN, bd=0, width=38)
        ent_nombre_zip.grid(row=3, column=1, sticky="ew", padx=8, pady=4)

        f_c.grid_columnconfigure(1, weight=1)

        self.btn_crear_respaldo = tk.Button(
            f_c,
            text="🗜 Crear Respaldo Ahora",
            font=("Segoe UI", 10, "bold"),
            bg=COLOR_PINK_INT,
            fg="#FFFFFF",
            bd=0,
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._iniciar_creacion_respaldo
        )
        self.btn_crear_respaldo.grid(row=4, column=0, columnspan=2, sticky="w", pady=(12, 0))

        # Lista de Respaldos
        c_list = self._crear_tarjeta(content, "RESPALDOS DISPONIBLES EN EL DESTINO", "📦")
        f_l = tk.Frame(c_list, bg=COLOR_CARD)
        f_l.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 14))

        f_tree_r = tk.Frame(f_l, bg=COLOR_CARD)
        f_tree_r.pack(fill=tk.BOTH, expand=True)

        cols_r = ("nombre", "tamano", "fecha")
        self.tree_respaldos = ttk.Treeview(f_tree_r, columns=cols_r, show="headings", height=5)
        self.tree_respaldos.heading("nombre", text="Archivo ZIP")
        self.tree_respaldos.heading("tamano", text="Tamaño (MB)")
        self.tree_respaldos.heading("fecha", text="Fecha")

        self.tree_respaldos.column("nombre", width=320, minwidth=150, stretch=True)
        self.tree_respaldos.column("tamano", width=100, minwidth=70, stretch=True)
        self.tree_respaldos.column("fecha", width=140, minwidth=100, stretch=True)

        sy_r = ttk.Scrollbar(f_tree_r, orient="vertical", command=self.tree_respaldos.yview, style="Vertical.TScrollbar")
        sx_r = ttk.Scrollbar(f_tree_r, orient="horizontal", command=self.tree_respaldos.xview, style="Horizontal.TScrollbar")
        self.tree_respaldos.configure(yscrollcommand=sy_r.set, xscrollcommand=sx_r.set)

        self.tree_respaldos.grid(row=0, column=0, sticky="nsew")
        sy_r.grid(row=0, column=1, sticky="ns")
        sx_r.grid(row=1, column=0, sticky="ew")

        f_tree_r.grid_rowconfigure(0, weight=1)
        f_tree_r.grid_columnconfigure(0, weight=1)

        f_act_r = tk.Frame(f_l, bg=COLOR_CARD)
        f_act_r.pack(fill=tk.X, pady=(8, 0))

        tk.Button(f_act_r, text="📥 Restaurar respaldo", font=("Segoe UI", 9, "bold"), bg=COLOR_PURPLE_MAIN, fg="#FFFFFF", bd=0, padx=10, pady=4, cursor="hand2", command=self._respaldo_restaurar).pack(side=tk.LEFT, padx=2)
        tk.Button(f_act_r, text="Abrir carpeta de respaldos", font=("Segoe UI", 9), bg=COLOR_SIDEBAR, fg=COLOR_TEXT_MAIN, bd=0, padx=8, pady=4, cursor="hand2", command=self._respaldo_abrir_carpeta).pack(side=tk.LEFT, padx=2)

        self._refrescar_lista_respaldos()

    def _respaldo_elegir_origen(self):
        sel = filedialog.askdirectory(initialdir=self.var_respaldo_origen.get(), parent=self)
        if sel:
            p = Path(sel)
            self.var_respaldo_origen.set(str(p))
            self.var_respaldo_nombre.set(logica.sugerir_nombre_respaldo(p))

    def _respaldo_cambiar_tipo_destino(self):
        tipo = self.var_respaldo_dest_tipo.get()
        if tipo == "bosgame":
            if logica.estado_bosgame.conectado:
                self.var_respaldo_destino.set(logica.estado_bosgame.ruta_red)
                self.btn_elegir_dest_resp.config(state="disabled")
            else:
                messagebox.showwarning("Sin conexión", "Conéctese a la BOSGAME en la Herramienta 6 primero.", parent=self)
                self.var_respaldo_dest_tipo.set("local")
        else:
            self.btn_elegir_dest_resp.config(state="normal")
            self.var_respaldo_destino.set(str(logica.obtener_ruta_workspace()))

        self._refrescar_lista_respaldos()

    def _respaldo_elegir_destino(self):
        sel = filedialog.askdirectory(initialdir=self.var_respaldo_destino.get(), parent=self)
        if sel:
            self.var_respaldo_destino.set(sel)
            self._refrescar_lista_respaldos()

    def _refrescar_lista_respaldos(self):
        dest = Path(self.var_respaldo_destino.get())
        for row in self.tree_respaldos.get_children():
            self.tree_respaldos.delete(row)

        items = logica.listar_respaldos_en_destino(dest)
        for it in items:
            self.tree_respaldos.insert("", "end", values=(it["nombre"], f"{it['tam_mb']} MB", it["fecha"]), tags=(str(it["ruta_completa"]),))

    def _iniciar_creacion_respaldo(self):
        origen = Path(self.var_respaldo_origen.get())
        destino = Path(self.var_respaldo_destino.get())
        nombre = self.var_respaldo_nombre.get().strip()

        if not origen.exists():
            messagebox.showerror("Error", "La carpeta de origen no existe.", parent=self)
            return

        tam_bytes = logica.calcular_tamano_carpeta(origen)
        if tam_bytes > 2 * (1024 ** 3):
            gb = tam_bytes / (1024 ** 3)
            if not messagebox.askyesno("Confirmar", f"La carpeta pesa aprox. {gb:.1f} GB. ¿Continuar?", parent=self):
                return

        self.btn_crear_respaldo.config(state="disabled")
        self.actualizar_estado(f"Comprimiendo '{origen.name}'...", 10)

        def worker():
            res = logica.crear_respaldo_zip(
                origen, destino, nombre,
                progress_callback=lambda pct, cur, tot: self.despachar_hilo_principal(lambda: self.actualizar_estado(f"Comprimiendo {cur}/{tot} ({pct}%)...", pct))
            )
            self.despachar_hilo_principal(lambda: self._finalizar_creacion_respaldo(res))

        threading.Thread(target=worker, daemon=True).start()

    def _finalizar_creacion_respaldo(self, resultado):
        self.btn_crear_respaldo.config(state="normal")
        self.actualizar_estado(resultado["mensaje"], 100)
        self._refrescar_lista_respaldos()

        if resultado["ok"]:
            self.datos_sesion["respaldo"] = resultado
            resumen = (
                f"{resultado['mensaje']}\n\n"
                f"• Archivos: {resultado['total_archivos']}\n"
                f"• Omitidos: {resultado['omitidos']}\n"
                f"• Tamaño original: {resultado['tam_original_mb']} MB\n"
                f"• Comprimido: {resultado['tam_comprimido_mb']} MB\n"
                f"• Reducción: {resultado['reduccion_pct']}%\n"
                f"• Tiempo: {resultado['duracion_segundos']} seg"
            )
            messagebox.showinfo("Respaldo Completado", resumen, parent=self)
        else:
            messagebox.showerror("Fallo", resultado["mensaje"], parent=self)

    def _respaldo_restaurar(self):
        item = self.tree_respaldos.selection()
        if not item:
            messagebox.showinfo("Selección", "Seleccione un archivo ZIP.", parent=self)
            return
        tags = self.tree_respaldos.item(item[0], "tags")
        if not tags:
            return
        zip_path = Path(tags[0])

        carpeta_dest = filedialog.askdirectory(title="Extraer contenido en:", parent=self)
        if not carpeta_dest:
            return

        res = logica.restaurar_respaldo_zip(zip_path, Path(carpeta_dest))
        if res["ok"]:
            self.actualizar_estado(res["mensaje"])
            messagebox.showinfo("Restauración", res["mensaje"], parent=self)
        else:
            messagebox.showerror("Error", res["mensaje"], parent=self)

    def _respaldo_abrir_carpeta(self):
        dest = Path(self.var_respaldo_destino.get())
        if dest.exists():
            subprocess.run(["explorer", str(dest)], creationflags=logica.NO_WINDOW)

    # ==========================================================================
    # HERRAMIENTA 8: EDITOR Y ENVÍO DE ARCHIVOS
    # ==========================================================================

    def _mostrar_herramienta_8(self):
        """Editor de texto y panel de envío (lado a lado en amplio, apilado en compacto)."""
        self._resaltar_boton_activo("8")
        self._limpiar_panel_central()

        self.scroll_activo = scroll_box = MarcoConScroll(self.center_frame)
        scroll_box.pack(fill=tk.BOTH, expand=True)
        content = scroll_box.interior

        # PARTE 1: EDITOR DE TEXTO
        c_edit = self._crear_tarjeta(content, "PARTE 1: EDITOR DE ARCHIVOS DE TEXTO LOCAL", "📝")
        f_ed = tk.Frame(c_edit, bg=COLOR_CARD)
        f_ed.pack(fill=tk.X, padx=16, pady=(0, 14))

        f_meta = tk.Frame(f_ed, bg=COLOR_CARD)
        f_meta.pack(fill=tk.X, pady=(0, 6))

        tk.Label(f_meta, text="Nombre (.txt):", font=("Segoe UI", 10, "bold"), fg=COLOR_PINK_SOFT, bg=COLOR_CARD).pack(side=tk.LEFT)
        self.var_editor_nombre = tk.StringVar(value="informe_diagnostico.txt")
        ent_nom = tk.Entry(f_meta, textvariable=self.var_editor_nombre, font=("Segoe UI", 10), bg=COLOR_SIDEBAR, fg=COLOR_TEXT_MAIN, bd=0, width=22)
        ent_nom.pack(side=tk.LEFT, padx=6)

        tk.Label(f_meta, text="Carpeta:", font=("Segoe UI", 10, "bold"), fg=COLOR_PINK_SOFT, bg=COLOR_CARD).pack(side=tk.LEFT, padx=(8, 4))
        self.var_editor_carpeta = tk.StringVar(value=str(logica.obtener_ruta_workspace()))
        ent_carp = tk.Entry(f_meta, textvariable=self.var_editor_carpeta, font=("Segoe UI", 10), bg=COLOR_SIDEBAR, fg=COLOR_TEXT_MAIN, bd=0, width=24)
        ent_carp.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        tk.Button(f_meta, text="📂", font=("Segoe UI", 9, "bold"), bg=COLOR_SIDEBAR, fg=COLOR_TEXT_MAIN, bd=0, padx=6, cursor="hand2", command=self._editor_elegir_carpeta).pack(side=tk.LEFT)

        # Text widget con scroll y wrap='word'
        f_txt_box = tk.Frame(f_ed, bg=COLOR_CARD)
        f_txt_box.pack(fill=tk.X, pady=6)

        self.txt_editor = tk.Text(
            f_txt_box,
            height=6,
            font=("Consolas", 10),
            bg=COLOR_SIDEBAR,
            fg=COLOR_TEXT_MAIN,
            bd=0,
            padx=8,
            pady=8,
            wrap="word",
            insertbackground="#FFFFFF"
        )
        sy_txt = ttk.Scrollbar(f_txt_box, orient="vertical", command=self.txt_editor.yview, style="Vertical.TScrollbar")
        self.txt_editor.configure(yscrollcommand=sy_txt.set)

        self.txt_editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sy_txt.pack(side=tk.RIGHT, fill=tk.Y)

        self.txt_editor.insert("1.0", "Diagnóstico del sistema operativo Windows.\nGenerado desde BrachioDiag por Angélica Serracín.")

        f_btn_ed = tk.Frame(f_ed, bg=COLOR_CARD)
        f_btn_ed.pack(fill=tk.X, pady=(6, 0))

        tk.Button(f_btn_ed, text="💾 Guardar archivo", font=("Segoe UI", 9, "bold"), bg=COLOR_PINK_INT, fg="#FFFFFF", bd=0, padx=10, pady=4, cursor="hand2", command=self._editor_guardar).pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(f_btn_ed, text="Abrir existente", font=("Segoe UI", 9), bg=COLOR_SIDEBAR, fg=COLOR_TEXT_MAIN, bd=0, padx=8, pady=4, cursor="hand2", command=self._editor_abrir).pack(side=tk.LEFT, padx=4)
        tk.Button(f_btn_ed, text="Limpiar", font=("Segoe UI", 9), bg=COLOR_SIDEBAR, fg=COLOR_TEXT_MUTED, bd=0, padx=8, pady=4, cursor="hand2", command=lambda: self.txt_editor.delete("1.0", tk.END)).pack(side=tk.LEFT, padx=4)

        # PARTE 2: PANEL DE ENVÍO ADAPTABLE
        c_env = self._crear_tarjeta(content, "PARTE 2: PANEL DE ENVÍO HACIA LA BOSGAME", "🚀")
        self.f_env_contenedor = tk.Frame(c_env, bg=COLOR_CARD)
        self.f_env_contenedor.pack(fill=tk.X, padx=16, pady=(0, 14))

        self._renderizar_panel_envio_responsive()

    def _renderizar_panel_envio_responsive(self):
        """Renderiza las 3 columnas lado a lado en modo amplio/medio, o apiladas en modo compacto."""
        for w in self.f_env_contenedor.winfo_children():
            w.destroy()

        es_compacto = (self.modo_responsive_actual == "compacto")

        # Columna 1: Mi Equipo
        col1 = tk.Frame(self.f_env_contenedor, bg=COLOR_SIDEBAR, padx=10, pady=8)
        if es_compacto:
            col1.pack(fill=tk.X, pady=(0, 6))
        else:
            col1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(col1, text="💻 Mi Equipo (Archivos locales)", font=("Segoe UI", 10, "bold"), fg=COLOR_PINK_SOFT, bg=COLOR_SIDEBAR).pack(anchor="w")

        self.lista_envio_local = tk.Listbox(
            col1, bg=COLOR_CARD, fg=COLOR_TEXT_MAIN, font=("Segoe UI", 10), bd=0, height=5 if es_compacto else 7, selectbackground=COLOR_PURPLE_MAIN
        )
        self.lista_envio_local.pack(fill=tk.BOTH, expand=True, pady=4)
        self.lista_envio_local.bind("<<ListboxSelect>>", lambda e: self._actualizar_estado_boton_envio())

        # Columna 2: Botón Enviar (Horizontal en compacto, vertical en amplio)
        col2 = tk.Frame(self.f_env_contenedor, bg=COLOR_CARD, padx=8, pady=4)
        if es_compacto:
            col2.pack(fill=tk.X, pady=4)
            btn_txt = "Enviar ⬇ hacia BOSGAME"
        else:
            col2.pack(side=tk.LEFT, fill=tk.Y)
            btn_txt = "Enviar ➔"

        self.btn_enviar_archivo = tk.Button(
            col2,
            text=btn_txt,
            font=("Segoe UI", 11, "bold"),
            bg=COLOR_PINK_INT,
            fg="#FFFFFF",
            activebackground=COLOR_PINK_SOFT,
            bd=0,
            padx=14,
            pady=8 if es_compacto else 14,
            cursor="hand2",
            command=self._iniciar_envio_archivo
        )
        self.btn_enviar_archivo.pack(fill=tk.X if es_compacto else tk.NONE, expand=True)

        # Columna 3: BOSGAME
        col3 = tk.Frame(self.f_env_contenedor, bg=COLOR_SIDEBAR, padx=10, pady=8)
        if es_compacto:
            col3.pack(fill=tk.X, pady=(6, 0))
        else:
            col3.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        tit_rem = f"📡 BOSGAME ({logica.estado_bosgame.carpeta or 'Sin conexión'})"
        tk.Label(col3, text=tit_rem, font=("Segoe UI", 10, "bold"), fg=COLOR_GREEN if logica.estado_bosgame.conectado else COLOR_YELLOW, bg=COLOR_SIDEBAR).pack(anchor="w")

        if logica.estado_bosgame.conectado:
            self.lista_envio_remota = tk.Listbox(
                col3, bg=COLOR_CARD, fg=COLOR_TEXT_MAIN, font=("Segoe UI", 10), bd=0, height=5 if es_compacto else 7, selectbackground=COLOR_PURPLE_MAIN
            )
            self.lista_envio_remota.pack(fill=tk.BOTH, expand=True, pady=4)
        else:
            self.lista_envio_remota = None
            f_av = tk.Frame(col3, bg=COLOR_SIDEBAR)
            f_av.pack(fill=tk.BOTH, expand=True, pady=8)
            tk.Label(f_av, text="Sin conexión activa a la BOSGAME.", font=("Segoe UI", 9), fg=COLOR_TEXT_MUTED, bg=COLOR_SIDEBAR).pack()
            tk.Button(f_av, text="Ir a Herramienta 6", font=("Segoe UI", 9, "bold"), bg=COLOR_PURPLE_MAIN, fg="#FFFFFF", bd=0, padx=8, pady=3, cursor="hand2", command=self._mostrar_herramienta_6).pack(pady=4)

        self._refrescar_listas_envio()

    def _editor_elegir_carpeta(self):
        sel = filedialog.askdirectory(initialdir=self.var_editor_carpeta.get(), parent=self)
        if sel:
            self.var_editor_carpeta.set(sel)
            self._refrescar_listas_envio()

    def _editor_guardar(self):
        carpeta = Path(self.var_editor_carpeta.get())
        nombre = self.var_editor_nombre.get().strip()
        contenido = self.txt_editor.get("1.0", tk.END).rstrip("\n")

        if not nombre.lower().endswith(".txt"):
            nombre += ".txt"
            self.var_editor_nombre.set(nombre)

        destino = carpeta / nombre
        if destino.exists():
            if not messagebox.askyesno("Confirmar", f"'{nombre}' ya existe. ¿Sobrescribirlo?", parent=self):
                return

        res = logica.guardar_archivo_texto(carpeta, nombre, contenido)
        if res["ok"]:
            self.actualizar_estado(res["mensaje"])
            self._refrescar_listas_envio()
            for i in range(self.lista_envio_local.size()):
                if self.lista_envio_local.get(i) == nombre:
                    self.lista_envio_local.selection_clear(0, tk.END)
                    self.lista_envio_local.selection_set(i)
                    self._actualizar_estado_boton_envio()
                    break
        else:
            messagebox.showerror("Error", res["mensaje"], parent=self)

    def _editor_abrir(self):
        sel = filedialog.askopenfilename(initialdir=self.var_editor_carpeta.get(), filetypes=[("Archivos TXT", "*.txt")], parent=self)
        if sel:
            res = logica.abrir_archivo_texto(Path(sel))
            if res["ok"]:
                self.var_editor_nombre.set(res["nombre"])
                self.var_editor_carpeta.set(str(Path(sel).parent))
                self.txt_editor.delete("1.0", tk.END)
                self.txt_editor.insert("1.0", res["contenido"])
                self._refrescar_listas_envio()
                self.actualizar_estado(f"Archivo cargado: {res['nombre']}")

    def _refrescar_listas_envio(self):
        self.lista_envio_local.delete(0, tk.END)
        carp = Path(self.var_editor_carpeta.get())
        if carp.exists():
            for f in sorted(carp.iterdir()):
                if f.is_file():
                    self.lista_envio_local.insert(tk.END, f.name)

        if self.lista_envio_remota and logica.estado_bosgame.conectado:
            self.lista_envio_remota.delete(0, tk.END)
            try:
                carp_r = Path(logica.estado_bosgame.ruta_red)
                for f in sorted(carp_r.iterdir()):
                    if f.is_file():
                        self.lista_envio_remota.insert(tk.END, f.name)
            except Exception:
                pass

        self._actualizar_estado_boton_envio()

    def _actualizar_estado_boton_envio(self):
        sel = self.lista_envio_local.curselection()
        if sel and logica.estado_bosgame.conectado:
            self.btn_enviar_archivo.config(state="normal", bg=COLOR_PINK_INT)
        else:
            self.btn_enviar_archivo.config(state="disabled", bg=COLOR_SIDEBAR)

    def _iniciar_envio_archivo(self):
        sel = self.lista_envio_local.curselection()
        if not sel:
            return

        nombre = self.lista_envio_local.get(sel[0])
        ruta_orig = Path(self.var_editor_carpeta.get()) / nombre

        self.btn_enviar_archivo.config(state="disabled")
        self.actualizar_estado(f"Enviando '{nombre}' a BOSGAME...", 30)

        def worker():
            res = logica.enviar_archivo_a_bosgame(ruta_orig)
            if not res["ok"] and res.get("ya_existe"):
                self.despachar_hilo_principal(lambda: self._resolver_conflicto_envio(ruta_orig))
                return
            self.despachar_hilo_principal(lambda: self._finalizar_envio_archivo(res))

        threading.Thread(target=worker, daemon=True).start()

    def _resolver_conflicto_envio(self, ruta_orig):
        op = messagebox.askyesnocancel("Conflicto", f"'{ruta_orig.name}' ya existe en BOSGAME.\n\n• Sí: Sobrescribir\n• No: Renombrar con fecha\n• Cancelar: Anular", parent=self)
        if op is True:
            threading.Thread(target=lambda: self.despachar_hilo_principal(lambda: self._finalizar_envio_archivo(
                logica.enviar_archivo_a_bosgame(ruta_orig, sobrescribir=True)
            )), daemon=True).start()
        elif op is False:
            threading.Thread(target=lambda: self.despachar_hilo_principal(lambda: self._finalizar_envio_archivo(
                logica.enviar_archivo_a_bosgame(ruta_orig, renombrar_con_timestamp=True)
            )), daemon=True).start()
        else:
            self.btn_enviar_archivo.config(state="normal")
            self.actualizar_estado("Envío cancelado.")

    def _finalizar_envio_archivo(self, resultado):
        self.btn_enviar_archivo.config(state="normal")
        self._refrescar_listas_envio()

        if resultado["ok"]:
            self.datos_sesion["envio"] = resultado
            self.actualizar_estado("Archivo enviado correctamente.", 100)
            nom = resultado.get("nombre_destino")
            if self.lista_envio_remota and nom:
                for idx in range(self.lista_envio_remota.size()):
                    if self.lista_envio_remota.get(idx) == nom:
                        self.lista_envio_remota.delete(idx)
                        self.lista_envio_remota.insert(idx, f"✓ {nom}")
                        self.lista_envio_remota.selection_set(idx)
                        break
            messagebox.showinfo("Envío Exitoso", resultado["mensaje"], parent=self)
        else:
            self.actualizar_estado("Error al transferir.")
            messagebox.showerror("Error", resultado["mensaje"], parent=self)

    # ==========================================================================
    # HERRAMIENTA 9: PERMISOS DE ARCHIVOS (ICACLS)
    # ==========================================================================

    def _mostrar_herramienta_9(self):
        """Asignación de permisos NTFS y pruebas en vivo de lectura/escritura."""
        self._resaltar_boton_activo("9")
        self._limpiar_panel_central()

        self.scroll_activo = scroll_box = MarcoConScroll(self.center_frame)
        scroll_box.pack(fill=tk.BOTH, expand=True)
        content = scroll_box.interior

        c_perm = self._crear_tarjeta(content, "CONTROL DE ACCESO Y SEGURIDAD NTFS (ICACLS)", "🔒")
        f_p = tk.Frame(c_perm, bg=COLOR_CARD)
        f_p.pack(fill=tk.X, padx=16, pady=(0, 14))

        # Archivo
        f_arch = tk.Frame(f_p, bg=COLOR_CARD)
        f_arch.pack(fill=tk.X, pady=(0, 8))

        tk.Label(f_arch, text="Archivo:", font=("Segoe UI", 10, "bold"), fg=COLOR_PINK_SOFT, bg=COLOR_CARD).pack(side=tk.LEFT)

        arch_default = logica.obtener_ruta_workspace() / "prueba_seguridad_ntfs.txt"
        if not arch_default.exists():
            with open(arch_default, "w", encoding="utf-8") as f:
                f.write("Archivo de prueba para la verificación de permisos NTFS en BrachioDiag.\n")

        self.var_permiso_archivo = tk.StringVar(value=str(arch_default))
        ent_arch = tk.Entry(f_arch, textvariable=self.var_permiso_archivo, font=("Segoe UI", 10), bg=COLOR_SIDEBAR, fg=COLOR_TEXT_MAIN, bd=0)
        ent_arch.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)

        tk.Button(f_arch, text="📂 Elegir", font=("Segoe UI", 9, "bold"), bg=COLOR_SIDEBAR, fg=COLOR_TEXT_MAIN, bd=0, padx=8, pady=3, cursor="hand2", command=self._permisos_elegir_archivo).pack(side=tk.RIGHT)

        # Usuario y Acción
        f_usr = tk.Frame(f_p, bg=COLOR_CARD)
        f_usr.pack(fill=tk.X, pady=6)

        tk.Label(f_usr, text="Usuario/Grupo:", font=("Segoe UI", 10, "bold"), fg=COLOR_PINK_SOFT, bg=COLOR_CARD).pack(side=tk.LEFT)
        usr_act = logica.accion_info_general()["usuario"]
        self.var_permiso_usuario = tk.StringVar(value=usr_act)
        cb_u = ttk.Combobox(f_usr, textvariable=self.var_permiso_usuario, values=[usr_act, "Todos", "Usuarios"], state="readonly", width=16)
        cb_u.pack(side=tk.LEFT, padx=(6, 16))

        tk.Label(f_usr, text="Acción:", font=("Segoe UI", 10, "bold"), fg=COLOR_PINK_SOFT, bg=COLOR_CARD).pack(side=tk.LEFT)
        self.var_permiso_accion = tk.StringVar(value="Denegar")

        tk.Radiobutton(f_usr, text="Permitir", variable=self.var_permiso_accion, value="Permitir", font=("Segoe UI", 10), fg=COLOR_TEXT_MAIN, bg=COLOR_CARD, selectcolor=COLOR_SIDEBAR).pack(side=tk.LEFT, padx=4)
        tk.Radiobutton(f_usr, text="Denegar", variable=self.var_permiso_accion, value="Denegar", font=("Segoe UI", 10), fg=COLOR_TEXT_MAIN, bg=COLOR_CARD, selectcolor=COLOR_SIDEBAR).pack(side=tk.LEFT, padx=4)

        # Casillas
        tk.Label(f_p, text="Seleccione permisos a modificar:", font=("Segoe UI", 10, "bold"), fg=COLOR_PURPLE_LGT, bg=COLOR_CARD).pack(anchor="w", pady=(8, 4))

        self.f_checks_perm = tk.Frame(f_p, bg=COLOR_SIDEBAR, padx=12, pady=8)
        self.f_checks_perm.pack(fill=tk.X, pady=4)

        self.check_vars = {
            "R": (tk.BooleanVar(value=False), "Lectura (R)", "Leer contenido"),
            "W": (tk.BooleanVar(value=True), "Escritura (W)", "Modificar y añadir datos"),
            "RX": (tk.BooleanVar(value=False), "Ejecución (RX)", "Ejecutar programas"),
            "M": (tk.BooleanVar(value=False), "Modificar (M)", "Lectura, escritura y borrado"),
            "D": (tk.BooleanVar(value=False), "Eliminar (D)", "Borrar archivo"),
            "F": (tk.BooleanVar(value=False), "Control total (F)", "Acceso absoluto"),
        }

        # Organizar casillas en 2 columnas (o 1 en compacto)
        cols_c = 2 if self.modo_responsive_actual != "compacto" else 1
        for i, (cod, (var, etiq, desc)) in enumerate(self.check_vars.items()):
            r = i if cols_c == 1 else i // 2
            c = 0 if cols_c == 1 else (i % 2) * 2

            tk.Checkbutton(self.f_checks_perm, text=etiq, variable=var, font=("Segoe UI", 10, "bold"), fg=COLOR_TEXT_MAIN, bg=COLOR_SIDEBAR, selectcolor=COLOR_CARD).grid(row=r, column=c, sticky="w", pady=2)
            tk.Label(self.f_checks_perm, text=f"- {desc}", font=("Segoe UI", 9), fg=COLOR_TEXT_MUTED, bg=COLOR_SIDEBAR).grid(row=r, column=c+1, sticky="w", padx=(4, 16), pady=2)

        # Botones
        f_btn_p = tk.Frame(f_p, bg=COLOR_CARD)
        f_btn_p.pack(fill=tk.X, pady=(10, 6))

        tk.Button(f_btn_p, text="🔒 Aplicar", font=("Segoe UI", 10, "bold"), bg=COLOR_PINK_INT, fg="#FFFFFF", bd=0, padx=12, pady=4, cursor="hand2", command=self._permisos_aplicar).pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(f_btn_p, text="📋 Ver actuales", font=("Segoe UI", 9, "bold"), bg=COLOR_SIDEBAR, fg=COLOR_TEXT_MAIN, bd=0, padx=8, pady=4, cursor="hand2", command=self._permisos_ver_actuales).pack(side=tk.LEFT, padx=3)
        tk.Button(f_btn_p, text="📖 Probar lectura", font=("Segoe UI", 9, "bold"), bg=COLOR_PURPLE_MAIN, fg="#FFFFFF", bd=0, padx=8, pady=4, cursor="hand2", command=self._permisos_probar_lectura).pack(side=tk.LEFT, padx=3)
        tk.Button(f_btn_p, text="✍ Probar escritura", font=("Segoe UI", 9, "bold"), bg=COLOR_PURPLE_MAIN, fg="#FFFFFF", bd=0, padx=8, pady=4, cursor="hand2", command=self._permisos_probar_escritura).pack(side=tk.LEFT, padx=3)
        tk.Button(f_btn_p, text="↺ Restaurar", font=("Segoe UI", 9), bg=COLOR_SIDEBAR, fg=COLOR_YELLOW, bd=0, padx=8, pady=4, cursor="hand2", command=self._permisos_restaurar).pack(side=tk.RIGHT)

        f_res_p = tk.Frame(f_p, bg=COLOR_CARD)
        f_res_p.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

        tk.Label(f_res_p, text="Salida de icacls:", font=("Segoe UI", 10, "bold"), fg=COLOR_PINK_SOFT, bg=COLOR_CARD).pack(anchor="w")

        self.txt_permisos_salida = tk.Text(f_res_p, height=6, font=("Consolas", 10), bg=COLOR_SIDEBAR, fg=COLOR_TEXT_MAIN, bd=0, padx=8, pady=6, wrap="word")
        self.txt_permisos_salida.pack(fill=tk.BOTH, expand=True, pady=4)

        self._permisos_ver_actuales()

    def _permisos_elegir_archivo(self):
        sel = filedialog.askopenfilename(initialdir=str(Path.home()), parent=self)
        if sel:
            p = Path(sel)
            if not logica.es_ruta_segura_usuario(p):
                messagebox.showwarning("Aviso", "Solo se permite en su directorio personal.", parent=self)
                return
            self.var_permiso_archivo.set(str(p))
            self._permisos_ver_actuales()

    def _permisos_ver_actuales(self):
        p = Path(self.var_permiso_archivo.get())
        if not p.exists():
            return
        res = logica.permisos_ver_actuales(p)
        self.txt_permisos_salida.delete("1.0", tk.END)
        self.txt_permisos_salida.insert("1.0", f"--- Permisos Actuales ({p.name}) ---\n{res.get('salida', '')}\n")

    def _permisos_aplicar(self):
        p = Path(self.var_permiso_archivo.get())
        usr = self.var_permiso_usuario.get()
        accion = self.var_permiso_accion.get()

        seleccionados = [cod for cod, (var, _, _) in self.check_vars.items() if var.get()]
        if not seleccionados:
            messagebox.showwarning("Aviso", "Marque al menos un permiso.", parent=self)
            return

        if accion == "Denegar" and usr == logica.accion_info_general()["usuario"]:
            if "R" in seleccionados or "F" in seleccionados:
                if not messagebox.askyesno("Advertencia", f"Está a punto de DENEGAR acceso a '{usr}'. ¿Continuar?", parent=self):
                    return

        res = logica.permisos_aplicar(p, usr, accion, seleccionados)
        self.txt_permisos_salida.insert(tk.END, f"\n[{accion.upper()} {','.join(seleccionados)} en '{usr}']\n")
        self.txt_permisos_salida.insert(tk.END, f"Comando: {res.get('comando', '')}\n{res.get('salida', '')}\n")
        self.txt_permisos_salida.see(tk.END)

        if res["ok"]:
            self.datos_sesion["permisos"] = res
            self.actualizar_estado(res["mensaje"])
        else:
            messagebox.showerror("Error", res["mensaje"], parent=self)

    def _permisos_probar_lectura(self):
        p = Path(self.var_permiso_archivo.get())
        res = logica.permisos_probar_lectura(p)
        self.txt_permisos_salida.insert(tk.END, f"\n[Prueba de Lectura]: {res['mensaje']}\n")
        self.txt_permisos_salida.see(tk.END)
        self.actualizar_estado(res["mensaje"], color=COLOR_GREEN if res["ok"] else COLOR_PINK_INT)

    def _permisos_probar_escritura(self):
        p = Path(self.var_permiso_archivo.get())
        res = logica.permisos_probar_escritura(p)
        self.txt_permisos_salida.insert(tk.END, f"\n[Prueba de Escritura]: {res['mensaje']}\n")
        self.txt_permisos_salida.see(tk.END)
        self.actualizar_estado(res["mensaje"], color=COLOR_GREEN if res["ok"] else COLOR_PINK_INT)

    def _permisos_restaurar(self):
        p = Path(self.var_permiso_archivo.get())
        res = logica.permisos_restaurar_originales(p)
        self.txt_permisos_salida.insert(tk.END, f"\n[Restauración]: {res['mensaje']}\n{res.get('salida', '')}\n")
        self.txt_permisos_salida.see(tk.END)
        self.actualizar_estado(res["mensaje"])

    # ==========================================================================
    # HERRAMIENTA 10: INFORME DE DIAGNÓSTICO
    # ==========================================================================

    def _mostrar_herramienta_10(self):
        """Generación del informe .txt y HTML interactivo."""
        self._resaltar_boton_activo("10")
        self._limpiar_panel_central()

        self.scroll_activo = scroll_box = MarcoConScroll(self.center_frame)
        scroll_box.pack(fill=tk.BOTH, expand=True)
        content = scroll_box.interior

        c_rep = self._crear_tarjeta(content, "COMPILACIÓN DEL INFORME DE DIAGNÓSTICO", "📄")
        f_r = tk.Frame(c_rep, bg=COLOR_CARD)
        f_r.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 14))

        tk.Label(
            f_r,
            text="Compila un informe formal con los resultados de todas las herramientas ejecutadas.\nLo no ejecutado se marca explícitamente como 'No ejecutado'.",
            font=("Segoe UI", 10),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_CARD,
            justify="left"
        ).pack(anchor="w", pady=(0, 10))

        f_btn_rep = tk.Frame(f_r, bg=COLOR_CARD)
        f_btn_rep.pack(fill=tk.X, pady=6)

        tk.Button(f_btn_rep, text="📑 Generar Informe", font=("Segoe UI", 10, "bold"), bg=COLOR_PINK_INT, fg="#FFFFFF", bd=0, padx=14, pady=6, cursor="hand2", command=self._generar_informe_accion).pack(side=tk.LEFT, padx=(0, 6))

        self.btn_abrir_html = tk.Button(
            f_btn_rep, text="🌐 Abrir HTML", font=("Segoe UI", 10, "bold"), bg=COLOR_PURPLE_MAIN, fg="#FFFFFF", bd=0, padx=12, pady=6, cursor="hand2", state="disabled", command=self._abrir_informe_html
        )
        self.btn_abrir_html.pack(side=tk.LEFT, padx=4)

        tk.Button(
            f_btn_rep, text="Abrir Carpeta", font=("Segoe UI", 9), bg=COLOR_SIDEBAR, fg=COLOR_TEXT_MAIN, bd=0, padx=10, pady=6, cursor="hand2", command=lambda: subprocess.run(["explorer", str(logica.obtener_ruta_workspace())], creationflags=logica.NO_WINDOW)
        ).pack(side=tk.LEFT, padx=4)

        tk.Label(f_r, text="Previsualización:", font=("Segoe UI", 10, "bold"), fg=COLOR_PINK_SOFT, bg=COLOR_CARD).pack(anchor="w", pady=(12, 4))

        f_txt_prev = tk.Frame(f_r, bg=COLOR_CARD)
        f_txt_prev.pack(fill=tk.BOTH, expand=True)

        self.txt_preview_informe = tk.Text(f_txt_prev, height=10, font=("Consolas", 9), bg=COLOR_SIDEBAR, fg=COLOR_TEXT_MAIN, bd=0, padx=8, pady=8, wrap="word")
        sy_prv = ttk.Scrollbar(f_txt_prev, orient="vertical", command=self.txt_preview_informe.yview, style="Vertical.TScrollbar")
        self.txt_preview_informe.configure(yscrollcommand=sy_prv.set)

        self.txt_preview_informe.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sy_prv.pack(side=tk.RIGHT, fill=tk.Y)

        self.ruta_informe_html_generado = None

    def _generar_informe_accion(self):
        self.actualizar_estado("Generando informe...", 50)

        if not self.datos_sesion["sistema"]:
            self.datos_sesion["sistema"] = logica.accion_info_general()
            self.datos_sesion["discos"] = logica.accion_espacio_disco()
            self.datos_sesion["red"] = logica.accion_configuracion_ip()

        res = logica.generar_informe_completo(self.datos_sesion)
        if res["ok"]:
            self.ruta_informe_html_generado = res["ruta_html"]
            self.btn_abrir_html.config(state="normal")

            try:
                with open(res["ruta_txt"], "r", encoding="utf-8") as f:
                    self.txt_preview_informe.delete("1.0", tk.END)
                    self.txt_preview_informe.insert("1.0", f.read())
            except Exception:
                pass

            self.actualizar_estado("Informe generado con éxito.", 100)
            messagebox.showinfo("Completado", f"Informe guardado en:\n{res['ruta_html']}", parent=self)
        else:
            messagebox.showerror("Error", res["mensaje"], parent=self)

    def _abrir_informe_html(self):
        if self.ruta_informe_html_generado and Path(self.ruta_informe_html_generado).exists():
            webbrowser.open(str(Path(self.ruta_informe_html_generado).resolve()))

    # ==========================================================================
    # APARTADO: ACERCA DE (LOGO GRANDE CENTRADO + AUTORÍA)
    # ==========================================================================

    def _mostrar_acerca_de(self):
        """Ficha de autoría limpia, centrada, con el logo oficial grande y mensaje de agradecimiento."""
        self._resaltar_boton_activo("acerca")
        self._limpiar_panel_central()

        self.scroll_activo = scroll_box = MarcoConScroll(self.center_frame)
        scroll_box.pack(fill=tk.BOTH, expand=True)
        content = scroll_box.interior

        c_acerca = self._crear_tarjeta(content)
        f_a = tk.Frame(c_acerca, bg=COLOR_CARD)
        f_a.pack(fill=tk.X, padx=24, pady=16)

        # Logo Grande Centrado
        lbl_logo_acerca = tk.Label(f_a, bg=COLOR_CARD)
        if self.img_logo_grande:
            if self.modo_responsive_actual == "compacto" and self.img_logo_grande_sub:
                lbl_logo_acerca.config(image=self.img_logo_grande_sub)
            else:
                lbl_logo_acerca.config(image=self.img_logo_grande)
        else:
            lbl_logo_acerca.config(text="🦕", font=("Segoe UI Emoji", 48), fg=COLOR_PINK_SOFT)
        lbl_logo_acerca.pack(anchor="center", pady=(6, 10))

        tk.Label(f_a, text="BrachioDiag", font=("Segoe UI", 18, "bold"), fg=COLOR_PINK_SOFT, bg=COLOR_CARD).pack(anchor="center")
        tk.Label(f_a, text="Herramienta de Diagnóstico para Windows", font=("Segoe UI", 10), fg=COLOR_TEXT_MUTED, bg=COLOR_CARD).pack(anchor="center", pady=(2, 14))

        # Cuadro de datos del estudiante
        f_box_info = tk.Frame(f_a, bg=COLOR_SIDEBAR, padx=20, pady=14, highlightbackground=COLOR_BORDER, highlightthickness=1)
        f_box_info.pack(fill=tk.X, pady=8)

        datos_acerca = [
            ("Estudiante:", "Angélica Serracín"),
            ("Materia:", "Sistemas Operativos"),
            ("Carrera:", "Licenciatura en Desarrollo y Gestión de Software"),
            ("Institución:", "Universidad Tecnológica de Panamá (UTP) - Centro Regional de Chiriquí"),
        ]

        for tit, val in datos_acerca:
            f_r = tk.Frame(f_box_info, bg=COLOR_SIDEBAR)
            f_r.pack(fill=tk.X, pady=3)
            tk.Label(f_r, text=tit, font=("Segoe UI", 11, "bold"), fg=COLOR_PURPLE_LGT, bg=COLOR_SIDEBAR, width=14, anchor="w").pack(side=tk.LEFT)
            tk.Label(f_r, text=val, font=("Segoe UI", 11), fg=COLOR_TEXT_MAIN, bg=COLOR_SIDEBAR).pack(side=tk.LEFT)

        # Mensaje destacado final
        f_dest = tk.Frame(f_a, bg=COLOR_SIDEBAR, padx=20, pady=16, highlightbackground=COLOR_BORDER, highlightthickness=1)
        f_dest.pack(fill=tk.X, pady=(16, 8))

        tk.Label(
            f_dest,
            text="¡Gracias por usar mi aplicación!",
            font=("Segoe UI", 14, "bold"),
            fg=COLOR_PINK_INT,
            bg=COLOR_SIDEBAR
        ).pack(anchor="center")

        self.actualizar_estado("Ficha técnica mostrada.")

    # ==========================================================================
    # REDIBUJADO RESPONSIVE DE LA PANTALLA ACTIVA
    # ==========================================================================

    def _redibujar_pantalla_activa_responsive(self, modo, ancho, cambio_modo):
        """Si cambia el modo responsive, reacomoda los elementos de la herramienta activa."""
        if not cambio_modo:
            return

        # Si estamos en la herramienta 8, reacomodar panel de envío (horizontal vs vertical)
        if self.seccion_activa == "8" and hasattr(self, "f_env_contenedor"):
            try:
                self._renderizar_panel_envio_responsive()
            except Exception:
                pass

        # Si estamos en la herramienta 6, reacomodar tarjeta de estadísticas
        elif self.seccion_activa == "6" and hasattr(self, "f_bos_stats"):
            try:
                self._renderizar_tarjeta_estadisticas_bosgame()
            except Exception:
                pass

        # Si estamos en la herramienta 1, reacomodar logo e info grid
        elif self.seccion_activa == "1" and hasattr(self, "lbl_logo_inicio"):
            try:
                if self.img_logo_grande:
                    if modo == "compacto" and self.img_logo_grande_sub:
                        self.lbl_logo_inicio.config(image=self.img_logo_grande_sub)
                    else:
                        self.lbl_logo_inicio.config(image=self.img_logo_grande)
            except Exception:
                pass

        # Si estamos en Acerca de, reacomodar logo
        elif self.seccion_activa == "acerca":
            try:
                self._mostrar_acerca_de()
            except Exception:
                pass

    # ==========================================================================
    # CONFIRMACIÓN AL SALIR
    # ==========================================================================

    def _confirmar_salida(self):
        if messagebox.askyesno("Salir de BrachioDiag", "¿Estás segura de que deseas salir de BrachioDiag?", parent=self):
            self._detener_monitor_si_activo()
            self.destroy()


def main():
    """Punto de inicio de la aplicación de escritorio responsive."""
    app = BrachioDiagApp()
    app.mainloop()


if __name__ == "__main__":
    main()
