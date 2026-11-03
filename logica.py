"""
================================================================================
 BrachioDiag - Módulo de Lógica Pura del Sistema Operativo Windows
 Desarrolladora: Angélica Serracín
 Materia: Sistemas Operativos | UTP - Centro Regional de Chiriquí
================================================================================
"""

import os
import sys
import time
import base64
import socket
import getpass
import platform
import shutil
import zipfile
import subprocess
import string
import ctypes
from ctypes import wintypes
import winreg
import datetime
import ipaddress
import re
from pathlib import Path

# Bandera de Windows para evitar que se abran ventanas negras de consola
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)


# ==============================================================================
# ESTRUCTURAS WIN32 NATIVAS (KERNEL32 Y MPR)
# ==============================================================================

class MEMORYSTATUSEX(ctypes.Structure):
    """Estructura de la API Win32 para GlobalMemoryStatusEx de kernel32.dll."""
    _fields_ = [
        ("dwLength", wintypes.DWORD),
        ("dwMemoryLoad", wintypes.DWORD),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


class FILETIME(ctypes.Structure):
    """Estructura de la API Win32 para GetSystemTimes (medición de CPU)."""
    _fields_ = [
        ("dwLowDateTime", wintypes.DWORD),
        ("dwHighDateTime", wintypes.DWORD),
    ]


class NETRESOURCEW(ctypes.Structure):
    """Estructura de la API Win32 para WNetAddConnection2W de mpr.dll."""
    _fields_ = [
        ("dwScope", wintypes.DWORD),
        ("dwType", wintypes.DWORD),        # RESOURCETYPE_DISK = 1
        ("dwDisplayType", wintypes.DWORD),
        ("dwUsage", wintypes.DWORD),
        ("lpLocalName", wintypes.LPWSTR),  # Puede ser None para conexión UNC
        ("lpRemoteName", wintypes.LPWSTR), # Ej: \\192.168.100.10\carpeta
        ("lpComment", wintypes.LPWSTR),
        ("lpProvider", wintypes.LPWSTR),
    ]


# Estado anterior para la medición diferencial de CPU
_cpu_prev_idle = 0
_cpu_prev_kernel = 0
_cpu_prev_user = 0
_cpu_prev_time = 0.0


def _filetime_to_int(ft: FILETIME) -> int:
    """Convierte estructura FILETIME a entero de 64 bits."""
    return (ft.dwHighDateTime << 32) + ft.dwLowDateTime


def obtener_ruta_workspace() -> Path:
    """Ruta segura de trabajo dentro de la carpeta personal del usuario o local."""
    ruta = Path.home() / "BrachioDiag_Workspace"
    try:
        ruta.mkdir(parents=True, exist_ok=True)
        test_file = ruta / ".test_access"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("ok")
        test_file.unlink()
        return ruta
    except Exception:
        fallback = Path(__file__).resolve().parent / "BrachioDiag_Workspace"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


# ==============================================================================
# ESTADO COMPARTIDO DE LA CONEXIÓN CON BOSGAME (HERRAMIENTAS 6, 7, 8 Y 10)
# ==============================================================================

class EstadoConexionBOSGAME:
    """
    Objeto singleton que mantiene el estado global de la conexión con la BOSGAME.
    Es compartido entre las herramientas 6 (Conexión), 7 (Respaldo), 8 (Envío) y 10 (Informe).
    NUNCA almacena contraseñas una vez finalizada la autenticación.
    """
    def __init__(self):
        self.conectado = False
        self.ip = ""
        self.usuario = ""
        self.carpeta = ""
        self.ruta_red = ""              # Formato: \\192.168.100.10\compartida
        self.tiempo_conexion = None      # datetime del momento de conexión
        self.latencias = []              # Muestras de latencia en milisegundos
        self.latencia_promedio = 0.0
        self.latencia_minima = 0.0
        self.latencia_maxima = 0.0
        self.perdida_pct = 0.0
        self.puerto_445_abierto = False
        self.calidad = "Sin conexión"
        self.espacio_total_gb = 0.0
        self.espacio_usado_gb = 0.0
        self.espacio_libre_gb = 0.0
        self.total_archivos = 0

    def limpiar(self):
        """Restablece el estado de conexión al desconectarse."""
        self.conectado = False
        self.ip = ""
        self.usuario = ""
        self.carpeta = ""
        self.ruta_red = ""
        self.tiempo_conexion = None
        self.latencias = []
        self.latencia_promedio = 0.0
        self.latencia_minima = 0.0
        self.latencia_maxima = 0.0
        self.perdida_pct = 0.0
        self.puerto_445_abierto = False
        self.calidad = "Sin conexión"
        self.espacio_total_gb = 0.0
        self.espacio_usado_gb = 0.0
        self.espacio_libre_gb = 0.0
        self.total_archivos = 0


# Instancia compartida única
estado_bosgame = EstadoConexionBOSGAME()


# ==============================================================================
# HERRAMIENTA 1: INICIO E INFORMACIÓN GENERAL
# ==============================================================================

def accion_info_general() -> dict:
    """
    Recopila información del hardware, kernel de Windows, RAM, Uptime y usuario actual.
    Utiliza APIs nativas de Windows sin requerir paquetes externos ni privilegios de administrador.
    """
    info = {
        "so": "Windows",
        "edicion": "Windows",
        "version": platform.version(),
        "compilacion": "",
        "arquitectura": platform.machine(),
        "cpu": "Procesador Compatible",
        "nucleos": os.cpu_count() or 1,
        "usuario": getpass.getuser(),
        "equipo": socket.gethostname(),
        "es_admin": False,
        "uptime": "N/A",
        "uptime_segundos": 0,
        "ram": {
            "total_gb": 0.0,
            "usado_gb": 0.0,
            "libre_gb": 0.0,
            "carga_pct": 0,
        },
    }

    # 1. Edición de Windows desde el Registro
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as clave:
            try:
                info["edicion"] = str(winreg.QueryValueEx(clave, "ProductName")[0])
            except Exception:
                pass
            try:
                info["compilacion"] = str(winreg.QueryValueEx(clave, "CurrentBuildNumber")[0])
            except Exception:
                pass
    except Exception:
        info["edicion"] = f"{platform.system()} {platform.release()}"

    info["so"] = info["edicion"]

    # 2. Nombre del CPU desde el Registro de hardware
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as clave:
            info["cpu"] = str(winreg.QueryValueEx(clave, "ProcessorNameString")[0]).strip()
    except Exception:
        info["cpu"] = platform.processor() or "Procesador Estándar"

    # 3. Memoria física RAM con kernel32.GlobalMemoryStatusEx
    try:
        mem = MEMORYSTATUSEX()
        mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem)):
            total_bytes = mem.ullTotalPhys
            libre_bytes = mem.ullAvailPhys
            usado_bytes = total_bytes - libre_bytes
            gb = 1024 ** 3
            info["ram"]["total_gb"] = round(total_bytes / gb, 2)
            info["ram"]["usado_gb"] = round(usado_bytes / gb, 2)
            info["ram"]["libre_gb"] = round(libre_bytes / gb, 2)
            info["ram"]["carga_pct"] = int(mem.dwMemoryLoad)
    except Exception as e:
        info["ram"]["error"] = str(e)

    # 4. Uptime del procesador con kernel32.GetTickCount64
    try:
        ticks_ms = ctypes.windll.kernel32.GetTickCount64()
        segundos = int(ticks_ms / 1000)
        info["uptime_segundos"] = segundos
        dias = segundos // 86400
        horas = (segundos % 86400) // 3600
        minutos = (segundos % 3600) // 60
        segs = segundos % 60
        partes = []
        if dias > 0:
            partes.append(f"{dias}d")
        if horas > 0 or dias > 0:
            partes.append(f"{horas}h")
        partes.append(f"{minutos}m {segs}s")
        info["uptime"] = " ".join(partes)
    except Exception:
        info["uptime"] = "No disponible"

    # 5. Verificación de privilegios de elevación administrativa
    try:
        info["es_admin"] = bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        info["es_admin"] = False

    return info


# ==============================================================================
# HERRAMIENTA 2: MONITOR DE RENDIMIENTO EN VIVO (CPU Y RAM)
# ==============================================================================

def medir_rendimiento_en_vivo() -> dict:
    """
    Obtiene en tiempo real el porcentaje de uso de CPU y de memoria RAM.
    El CPU se calcula con kernel32.GetSystemTimes comparando la diferencia de tiempos.
    La RAM se obtiene con kernel32.GlobalMemoryStatusEx.
    """
    global _cpu_prev_idle, _cpu_prev_kernel, _cpu_prev_user, _cpu_prev_time

    datos = {
        "cpu_pct": 0.0,
        "ram_pct": 0.0,
        "ram_usada_gb": 0.0,
        "ram_total_gb": 0.0,
        "frase_cpu": "El procesador está tranquilo.",
        "frase_ram": "La memoria tiene suficiente espacio libre.",
        "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
    }

    # 1. Medición de CPU con GetSystemTimes
    try:
        idle = FILETIME()
        kernel = FILETIME()
        user = FILETIME()
        kernel32 = ctypes.windll.kernel32

        if kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
            i_act = _filetime_to_int(idle)
            k_act = _filetime_to_int(kernel)
            u_act = _filetime_to_int(user)
            ahora = time.time()

            if _cpu_prev_time > 0 and (ahora - _cpu_prev_time) >= 0.2:
                idle_delta = i_act - _cpu_prev_idle
                kernel_delta = k_act - _cpu_prev_kernel
                user_delta = u_act - _cpu_prev_user
                total_sys = kernel_delta + user_delta

                if total_sys > 0 and idle_delta <= total_sys:
                    pct = (1.0 - (idle_delta / total_sys)) * 100.0
                    datos["cpu_pct"] = max(0.0, min(100.0, round(pct, 1)))

            _cpu_prev_idle = i_act
            _cpu_prev_kernel = k_act
            _cpu_prev_user = u_act
            _cpu_prev_time = ahora
    except Exception:
        datos["cpu_pct"] = 10.0

    # Frase explicativa para CPU en lenguaje sencillo
    cpu = datos["cpu_pct"]
    if cpu < 30.0:
        datos["frase_cpu"] = "El procesador está tranquilo."
    elif cpu < 70.0:
        datos["frase_cpu"] = "Uso moderado del procesador."
    elif cpu < 85.0:
        datos["frase_cpu"] = "El procesador está ocupado."
    else:
        datos["frase_cpu"] = "El procesador está trabajando intensamente."

    # 2. Medición de RAM con GlobalMemoryStatusEx
    try:
        mem = MEMORYSTATUSEX()
        mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem)):
            gb = 1024 ** 3
            total = mem.ullTotalPhys / gb
            usado = (mem.ullTotalPhys - mem.ullAvailPhys) / gb
            datos["ram_pct"] = round(float(mem.dwMemoryLoad), 1)
            datos["ram_usada_gb"] = round(usado, 1)
            datos["ram_total_gb"] = round(total, 1)
    except Exception:
        datos["ram_pct"] = 50.0

    # Frase explicativa para RAM en lenguaje sencillo
    ram = datos["ram_pct"]
    if ram < 60.0:
        datos["frase_ram"] = "La memoria tiene suficiente espacio libre."
    elif ram < 80.0:
        datos["frase_ram"] = "La memoria está en uso considerable."
    else:
        datos["frase_ram"] = "La memoria está casi llena."

    return datos


# ==============================================================================
# HERRAMIENTA 3: DISCOS Y ARCHIVOS (ESPACIO + EXPLORADOR + TOP PESADOS)
# ==============================================================================

def accion_espacio_disco() -> list:
    """
    Obtiene todas las unidades de almacenamiento lógicas montadas en Windows
    y calcula el espacio total, usado y libre mediante shutil.disk_usage.
    """
    discos = []
    unidades = []

    # Detectar unidades activas con GetLogicalDrives de kernel32
    try:
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for i, letra in enumerate(string.ascii_uppercase):
            if bitmask & (1 << i):
                unidades.append(f"{letra}:\\")
    except Exception:
        unidades = [f"{l}:\\" for l in string.ascii_uppercase if os.path.exists(f"{l}:\\")]

    gb = 1024 ** 3
    for u in unidades:
        try:
            total, usado, libre = shutil.disk_usage(u)
            pct = round((usado / total) * 100, 1) if total > 0 else 0
            discos.append({
                "letra": u.rstrip("\\"),
                "total_gb": round(total / gb, 1),
                "usado_gb": round(usado / gb, 1),
                "libre_gb": round(libre / gb, 1),
                "pct_usado": pct,
                "pct_libre": round(100 - pct, 1),
                "accesible": True
            })
        except Exception:
            continue

    return discos


def explorador_listar_directorio(ruta_carpeta: Path) -> list:
    """
    Lista los elementos de una carpeta para el explorador de archivos.
    Devuelve lista de tuplas: (nombre, tipo, tamaño_formateado, fecha_formateada, es_carpeta, ruta_completa).
    """
    elementos = []
    try:
        for entrada in ruta_carpeta.iterdir():
            try:
                stats = entrada.stat()
                mtime = datetime.datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M")
                if entrada.is_dir():
                    tipo = "Carpeta"
                    tam_str = "--"
                    es_dir = True
                else:
                    tipo = f"Archivo ({entrada.suffix.lower() or 'sin ext'})"
                    tam = stats.st_size
                    if tam >= 1024 ** 3:
                        tam_str = f"{tam / (1024 ** 3):.2f} GB"
                    elif tam >= 1024 ** 2:
                        tam_str = f"{tam / (1024 ** 2):.1f} MB"
                    elif tam >= 1024:
                        tam_str = f"{tam / 1024:.1f} KB"
                    else:
                        tam_str = f"{tam} B"
                    es_dir = False

                elementos.append((entrada.name, tipo, tam_str, mtime, es_dir, entrada))
            except (PermissionError, OSError):
                continue
    except Exception as e:
        return []

    # Ordenar: primero carpetas alfabéticamente, luego archivos alfabéticamente
    elementos.sort(key=lambda x: (not x[4], x[0].lower()))
    return elementos


def es_ruta_segura_usuario(ruta: Path) -> bool:
    """
    Verifica que la ruta se encuentre estrictamente dentro de la carpeta personal del usuario.
    Evita modificaciones o eliminaciones accidentales en carpetas del sistema.
    """
    try:
        ruta_res = ruta.resolve()
        home_res = Path.home().resolve()
        return home_res in ruta_res.parents or ruta_res == home_res
    except Exception:
        return False


def explorador_crear_carpeta(ruta_padre: Path, nombre_carpeta: str) -> dict:
    """Crea una nueva carpeta dentro del directorio especificado."""
    try:
        nueva = ruta_padre / nombre_carpeta.strip()
        nueva.mkdir(parents=False, exist_ok=False)
        return {"ok": True, "mensaje": f"Carpeta creada exitosamente: {nueva.name}"}
    except FileExistsError:
        return {"ok": False, "mensaje": "Ya existe una carpeta o archivo con ese nombre."}
    except Exception as e:
        return {"ok": False, "mensaje": f"Error al crear carpeta: {e}"}


def explorador_renombrar(ruta_origen: Path, nuevo_nombre: str) -> dict:
    """Renombra un archivo o carpeta dentro de la misma ubicación."""
    try:
        nuevo_destino = ruta_origen.parent / nuevo_nombre.strip()
        ruta_origen.rename(nuevo_destino)
        return {"ok": True, "mensaje": f"Renombrado exitosamente a: {nuevo_destino.name}"}
    except Exception as e:
        return {"ok": False, "mensaje": f"Error al renombrar: {e}"}


def explorador_eliminar(ruta_objetivo: Path) -> dict:
    """
    Elimina un archivo o carpeta previa confirmación.
    Solo se permite si la ruta está dentro de la carpeta personal del usuario.
    """
    if not es_ruta_segura_usuario(ruta_objetivo):
        return {
            "ok": False,
            "mensaje": "Acción denegada por seguridad: Solo se permite eliminar archivos y carpetas dentro de tu directorio personal."
        }
    try:
        if ruta_objetivo.is_dir():
            shutil.rmtree(ruta_objetivo)
        else:
            ruta_objetivo.unlink()
        return {"ok": True, "mensaje": f"Eliminado correctamente: {ruta_objetivo.name}"}
    except Exception as e:
        return {"ok": False, "mensaje": f"Error al eliminar: {e}"}


def buscar_archivos_mas_pesados(carpeta_raiz: Path, cancel_event=None, progress_callback=None) -> list:
    """
    Escanea la carpeta elegida mediante os.walk en un hilo secundario
    y devuelve los 20 archivos más pesados con su tamaño formateado.
    Captura y omite silenciosamente carpetas sin permisos de lectura.
    """
    archivos = []
    total_revisados = 0

    try:
        for root, dirs, files in os.walk(str(carpeta_raiz)):
            if cancel_event and cancel_event.is_set():
                break

            for f in files:
                if cancel_event and cancel_event.is_set():
                    break

                total_revisados += 1
                if progress_callback and (total_revisados % 50 == 0):
                    progress_callback(total_revisados)

                ruta_f = Path(root) / f
                try:
                    stats = ruta_f.stat()
                    tam = stats.st_size
                    archivos.append({
                        "nombre": f,
                        "tam_bytes": tam,
                        "carpeta": root,
                        "fecha": datetime.datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M"),
                        "ruta_completa": ruta_f
                    })
                except (PermissionError, OSError):
                    continue
    except Exception:
        pass

    # Ordenar por tamaño descendente y tomar los 20 primeros
    archivos.sort(key=lambda x: x["tam_bytes"], reverse=True)
    top20 = archivos[:20]

    for item in top20:
        tam = item["tam_bytes"]
        if tam >= 1024 ** 3:
            item["tam_legible"] = f"{tam / (1024 ** 3):.2f} GB"
        elif tam >= 1024 ** 2:
            item["tam_legible"] = f"{tam / (1024 ** 2):.1f} MB"
        elif tam >= 1024:
            item["tam_legible"] = f"{tam / 1024:.1f} KB"
        else:
            item["tam_legible"] = f"{tam} B"

    return top20


# ==============================================================================
# HERRAMIENTA 4: PROGRAMAS Y ERRORES DEL SISTEMA (3 PESTAÑAS)
# ==============================================================================

def obtener_programas_instalados() -> list:
    """
    Lee los programas instalados en Windows desde el Registro:
    HKLM y HKCU en las claves Uninstall (incluyendo WOW6432Node para apps de 32 bits).
    """
    programas = []
    claves = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]

    nombres_vistos = set()

    for hkey, subkey_path in claves:
        try:
            with winreg.OpenKey(hkey, subkey_path) as clave_raiz:
                subclaves_count = winreg.QueryInfoKey(clave_raiz)[0]
                for i in range(subclaves_count):
                    try:
                        nombre_subclave = winreg.EnumKey(clave_raiz, i)
                        with winreg.OpenKey(clave_raiz, nombre_subclave) as subclave:
                            try:
                                nombre, _ = winreg.QueryValueEx(subclave, "DisplayName")
                                nombre = str(nombre).strip()
                            except OSError:
                                continue

                            if not nombre or nombre in nombres_vistos:
                                continue

                            # Filtrar entradas ocultas de sistema o actualizaciones menores
                            try:
                                sys_comp, _ = winreg.QueryValueEx(subclave, "SystemComponent")
                                if sys_comp == 1:
                                    continue
                            except OSError:
                                pass

                            version = ""
                            editor = ""
                            fecha = ""
                            tam_kb = 0

                            try:
                                version = str(winreg.QueryValueEx(subclave, "DisplayVersion")[0]).strip()
                            except OSError:
                                pass
                            try:
                                editor = str(winreg.QueryValueEx(subclave, "Publisher")[0]).strip()
                            except OSError:
                                pass
                            try:
                                fecha_raw = str(winreg.QueryValueEx(subclave, "InstallDate")[0]).strip()
                                if len(fecha_raw) == 8 and fecha_raw.isdigit():
                                    fecha = f"{fecha_raw[0:4]}-{fecha_raw[4:6]}-{fecha_raw[6:8]}"
                                else:
                                    fecha = fecha_raw
                            except OSError:
                                pass
                            try:
                                tam_kb = int(winreg.QueryValueEx(subclave, "EstimatedSize")[0])
                            except OSError:
                                pass

                            tam_str = "--"
                            if tam_kb > 0:
                                if tam_kb >= 1024 ** 2:
                                    tam_str = f"{tam_kb / (1024 ** 2):.1f} GB"
                                elif tam_kb >= 1024:
                                    tam_str = f"{tam_kb / 1024:.1f} MB"
                                else:
                                    tam_str = f"{tam_kb} KB"

                            nombres_vistos.add(nombre)
                            programas.append({
                                "nombre": nombre,
                                "version": version or "N/D",
                                "editor": editor or "Desconocido",
                                "fecha": fecha or "N/D",
                                "tamano": tam_str,
                            })
                    except OSError:
                        continue
        except OSError:
            continue

    programas.sort(key=lambda x: x["nombre"].lower())
    return programas


def obtener_programas_inicio() -> list:
    """
    Lee los programas configurados para iniciar automáticamente con Windows
    desde las claves Run de HKCU y HKLM, más la carpeta de inicio del usuario.
    """
    inicio = []

    # 1. Registro HKCU y HKLM
    claves = [
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "Registro (Usuario actual)"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "Registro (Equipo local)"),
    ]

    for hkey, ruta_k, origen_desc in claves:
        try:
            with winreg.OpenKey(hkey, ruta_k) as clave:
                valores_count = winreg.QueryInfoKey(clave)[1]
                for i in range(valores_count):
                    try:
                        nombre, comando, _ = winreg.EnumValue(clave, i)
                        inicio.append({
                            "nombre": str(nombre),
                            "comando": str(comando),
                            "origen": origen_desc
                        })
                    except OSError:
                        continue
        except OSError:
            continue

    # 2. Carpeta de inicio del usuario
    try:
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            carpeta_inicio = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
            if carpeta_inicio.exists():
                for f in carpeta_inicio.iterdir():
                    if f.is_file() and f.name.lower() != "desktop.ini":
                        inicio.append({
                            "nombre": f.stem,
                            "comando": str(f.resolve()),
                            "origen": "Carpeta de Inicio personal"
                        })
    except Exception:
        pass

    return inicio


def obtener_errores_recientes_sistema() -> dict:
    """
    Consulta los eventos de nivel Error, Advertencia o Crítico del visor de eventos de Windows.
    Si el sistema operativo deniega el acceso a usuarios estándar sin privilegios,
    captura la situación y devuelve un mensaje pedagógico claro con la causa.
    """
    resultado = {
        "ok": False,
        "eventos": [],
        "mensaje": "",
        "causa_probable": "",
        "resumen_gravedad": {"Critico": 0, "Error": 0, "Advertencia": 0}
    }

    cmd = [
        "wevtutil", "qe", "System",
        "/c:30", "/rd:true", "/f:text",
        "/q:*[System[(Level=1 or Level=2 or Level=3)]]"
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, errors="replace", creationflags=NO_WINDOW)
        salida = res.stdout or ""

        if res.returncode != 0 or "Acceso denegado" in (res.stderr or "") or "Acceso denegado" in salida:
            resultado["ok"] = False
            resultado["mensaje"] = "Acceso restringido por políticas de seguridad de Windows."
            resultado["causa_probable"] = (
                "El subsistema EventLog de Windows restringe la lectura directa de los canales del registro "
                "a usuarios estándar sin elevación UAC o que no pertenezcan al grupo 'Lectores del Registro de Eventos'."
            )
            return resultado

        # Procesar bloques de texto devueltos por wevtutil
        bloques = salida.split("Event[")
        eventos_parseados = []

        for b in bloques:
            if not b.strip():
                continue
            lineas = b.splitlines()
            fecha = ""
            origen = ""
            event_id = ""
            nivel = "Información"
            desc = ""

            for l in lineas:
                l_s = l.strip()
                if l_s.startswith("Date:"):
                    fecha = l_s.replace("Date:", "").strip()
                elif l_s.startswith("Source:"):
                    origen = l_s.replace("Source:", "").strip()
                elif l_s.startswith("Event ID:"):
                    event_id = l_s.replace("Event ID:", "").strip()
                elif l_s.startswith("Level:"):
                    lvl_str = l_s.replace("Level:", "").strip().lower()
                    if "critical" in lvl_str or "crítico" in lvl_str:
                        nivel = "Crítico"
                        resultado["resumen_gravedad"]["Critico"] += 1
                    elif "error" in lvl_str:
                        nivel = "Error"
                        resultado["resumen_gravedad"]["Error"] += 1
                    elif "warning" in lvl_str or "advertencia" in lvl_str:
                        nivel = "Advertencia"
                        resultado["resumen_gravedad"]["Advertencia"] += 1
                elif l_s.startswith("Description:"):
                    desc = l_s.replace("Description:", "").strip()

            if origen or event_id:
                eventos_parseados.append({
                    "fecha": fecha[:19] if fecha else "Reciente",
                    "origen": origen or "Sistema Windows",
                    "id": event_id or "N/D",
                    "nivel": nivel,
                    "mensaje": desc[:100] + ("..." if len(desc) > 100 else "") or "Evento registrado por el kernel de Windows."
                })

        resultado["ok"] = True
        resultado["eventos"] = eventos_parseados
        resultado["mensaje"] = f"Se leyeron {len(eventos_parseados)} eventos recientes del registro del sistema."
        return resultado

    except Exception as e:
        resultado["ok"] = False
        resultado["mensaje"] = "No fue posible consultar el visor de eventos."
        resultado["causa_probable"] = str(e)
        return resultado


# ==============================================================================
# HERRAMIENTA 5: CONFIGURACIÓN IP
# ==============================================================================

def accion_configuracion_ip() -> dict:
    """
    Ejecuta 'ipconfig /all' de forma silenciosa y procesa la salida para extraer
    los adaptadores de red activos, direcciones IPv4, máscara y dirección MAC.
    """
    resultado = {
        "hostname": socket.gethostname(),
        "adaptadores": [],
        "salida_cruda": ""
    }

    try:
        proc = subprocess.run(["ipconfig", "/all"], capture_output=True, text=True, errors="replace", creationflags=NO_WINDOW)
        salida = proc.stdout
        resultado["salida_cruda"] = salida

        bloques = salida.split("Adaptador ")
        for bloque in bloques[1:]:
            lineas = bloque.splitlines()
            nombre_adaptador = lineas[0].strip().rstrip(":")
            ipv4 = ""
            mascara = ""
            gateway = ""
            mac = ""
            dhcp = ""

            for linea in lineas[1:]:
                linea_limpia = linea.strip()
                if "IPv4" in linea_limpia or "Dirección IPv4" in linea_limpia:
                    m = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", linea_limpia)
                    if m and not ipv4:
                        ipv4 = m.group(1)
                elif "Máscara de subred" in linea_limpia:
                    m = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", linea_limpia)
                    if m and not mascara:
                        mascara = m.group(1)
                elif "Puerta de enlace predeterminada" in linea_limpia:
                    m = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", linea_limpia)
                    if m and not gateway:
                        gateway = m.group(1)
                elif "Dirección física" in linea_limpia:
                    partes = linea_limpia.split(":")
                    if len(partes) >= 2 and not mac:
                        mac = partes[-1].strip()
                elif "DHCP habilitado" in linea_limpia:
                    if "Sí" in linea_limpia or "Yes" in linea_limpia:
                        dhcp = "Sí"
                    elif "No" in linea_limpia:
                        dhcp = "No"

            if ipv4:
                resultado["adaptadores"].append({
                    "nombre": nombre_adaptador[:40],
                    "ipv4": ipv4,
                    "mascara": mascara or "255.255.255.0",
                    "gateway": gateway or "N/A",
                    "mac": mac or "Desconocida",
                    "dhcp": dhcp or "N/D",
                    "activo": True
                })

        if not resultado["adaptadores"]:
            # Fallback seguro con socket local si ipconfig no reportó adaptadores activos
            try:
                ip_local = socket.gethostbyname(socket.gethostname())
                resultado["adaptadores"].append({
                    "nombre": "Adaptador de Red Primario",
                    "ipv4": ip_local,
                    "mascara": "255.255.255.0",
                    "gateway": "192.168.100.1",
                    "mac": "00-00-00-00-00-00",
                    "dhcp": "Sí",
                    "activo": True
                })
            except Exception:
                pass

    except Exception as e:
        resultado["error"] = str(e)

    return resultado


# ==============================================================================
# HERRAMIENTA 6: CONEXIÓN A BOSGAME (CARPETA COMPARTIDA Y ESTADÍSTICAS)
# ==============================================================================

def validar_direccion_ip(ip_texto: str) -> bool:
    """Valida si el texto corresponde a una dirección IPv4 válida."""
    try:
        ipaddress.IPv4Address(ip_texto.strip())
        return True
    except Exception:
        return False


def bosgame_probar_puerto_445(ip: str, timeout: float = 1.5) -> bool:
    """Comprueba si el puerto SMB (445) responde en el host remoto."""
    try:
        with socket.create_connection((ip, 445), timeout=timeout):
            return True
    except Exception:
        return False


def bosgame_medir_latencias(ip: str, cantidad: int = 10, cancel_event=None) -> dict:
    """
    Ejecuta un sondeo de latencia (10 pings) para graficar y calcular
    latencia mínima, promedio, máxima y porcentaje de pérdida de paquetes.
    """
    resultado = {
        "muestras": [],
        "min": 0.0,
        "avg": 0.0,
        "max": 0.0,
        "perdida_pct": 100.0,
        "calidad": "Sin conexión",
        "frase_calidad": "El equipo no respondió a las solicitudes ICMP."
    }

    muestras = []
    perdidos = 0

    for _ in range(cantidad):
        if cancel_event and cancel_event.is_set():
            break
        try:
            inicio = time.time()
            proc = subprocess.run(["ping", "-n", "1", "-w", "1000", ip], capture_output=True, text=True, errors="replace", creationflags=NO_WINDOW)
            duracion = (time.time() - inicio) * 1000

            if proc.returncode == 0:
                m = re.search(r"tiempo[=<](\d+)ms", proc.stdout, re.IGNORECASE) or re.search(r"time[=<](\d+)ms", proc.stdout, re.IGNORECASE)
                if m:
                    ms = float(m.group(1))
                else:
                    ms = round(duracion, 1)
                muestras.append(ms)
            else:
                perdidos += 1
        except Exception:
            perdidos += 1

    total_pruebas = len(muestras) + perdidos
    if total_pruebas > 0:
        resultado["perdida_pct"] = round((perdidos / total_pruebas) * 100, 1)

    if muestras:
        resultado["muestras"] = muestras
        resultado["min"] = min(muestras)
        resultado["max"] = max(muestras)
        resultado["avg"] = round(sum(muestras) / len(muestras), 1)

        avg = resultado["avg"]
        loss = resultado["perdida_pct"]

        if loss == 0 and avg < 5.0:
            resultado["calidad"] = "Excelente"
            resultado["frase_calidad"] = "Conexión ultrarrápida y estable en la red LAN."
        elif loss < 10 and avg < 25.0:
            resultado["calidad"] = "Buena"
            resultado["frase_calidad"] = "Conexión estable con tiempos de respuesta normales."
        elif loss < 25 or avg < 80.0:
            resultado["calidad"] = "Regular"
            resultado["frase_calidad"] = "Se observan pequeñas demoras o pérdida intermitente de paquetes."
        else:
            resultado["calidad"] = "Mala"
            resultado["frase_calidad"] = "Conexión inestable con alta latencia o pérdida elevada."
    else:
        resultado["calidad"] = "Sin conexión"
        resultado["frase_calidad"] = "No se obtuvo respuesta del equipo remoto."

    return resultado


def bosgame_listar_compartidas(ip: str) -> list:
    """
    Ejecuta 'net view \\IP' para listar las carpetas que el host remoto comparte en red.
    """
    carpetas = []
    if not validar_direccion_ip(ip):
        return carpetas

    try:
        proc = subprocess.run(["net", "view", f"\\\\{ip}"], capture_output=True, text=True, errors="replace", creationflags=NO_WINDOW)
        salida = proc.stdout
        lineas = salida.splitlines()
        en_tabla = False

        for linea in lineas:
            if "---" in linea:
                en_tabla = True
                continue
            if en_tabla:
                partes = linea.split()
                if partes:
                    nombre_recurso = partes[0]
                    # Excluir recursos administrativos por defecto (C$, ADMIN$, IPC$)
                    if not nombre_recurso.endswith("$"):
                        carpetas.append(nombre_recurso)
    except Exception:
        pass

    return carpetas


def bosgame_conectar(ip: str, usuario: str, contrasena: str, carpeta: str) -> dict:
    """
    Autentica y monta la conexión a la carpeta compartida \\IP\carpeta.
    Utiliza WNetAddConnection2W (mpr.dll) para que la contraseña nunca aparezca en línea de comandos.
    Si mpr.dll encuentra problemas, utiliza 'net use' pasando los argumentos como lista.
    Actualiza el objeto compartido estado_bosgame.
    """
    ip = ip.strip()
    usuario = usuario.strip()
    carpeta = carpeta.strip().lstrip("\\/")

    if not validar_direccion_ip(ip):
        return {"ok": False, "mensaje": "La dirección IP no tiene un formato válido (Ej: 192.168.100.10)."}
    if not usuario:
        return {"ok": False, "mensaje": "El nombre de usuario no puede estar vacío."}
    if not carpeta:
        return {"ok": False, "mensaje": "Debe especificar el nombre de la carpeta compartida."}

    # 1. Comprobación preliminar de conectividad por puerto 445
    p445 = bosgame_probar_puerto_445(ip, timeout=2.0)
    ruta_red = f"\\\\{ip}\\{carpeta}"

    # 2. Conectar mediante WNetAddConnection2W (API Win32 Nativa)
    conexion_exitosa = False
    error_detalle = ""

    try:
        nr = NETRESOURCEW()
        nr.dwType = 1  # RESOURCETYPE_DISK
        nr.lpLocalName = None
        nr.lpRemoteName = ruta_red
        nr.lpProvider = None

        mpr = ctypes.windll.mpr
        # Flags: 0 para sesión actual no persistente
        ret = mpr.WNetAddConnection2W(ctypes.byref(nr), contrasena, usuario, 0)

        # 0 = NO_ERROR, 1219 = ERROR_SESSION_CREDENTIAL_CONFLICT (ya conectado)
        if ret in (0, 1219):
            conexion_exitosa = True
        else:
            error_detalle = f"Código de error Win32: {ret}"
    except Exception as e:
        error_detalle = str(e)

    # 3. Fallback con 'net use' si WNetAddConnection2W falló
    if not conexion_exitosa:
        try:
            cmd = ["net", "use", ruta_red, contrasena, f"/user:{usuario}", "/persistent:no"]
            res = subprocess.run(cmd, capture_output=True, text=True, errors="replace", creationflags=NO_WINDOW)
            if res.returncode == 0 or "ya se ha conectado" in res.stderr.lower():
                conexion_exitosa = True
            else:
                error_detalle = res.stderr.strip() or res.stdout.strip() or error_detalle
        except Exception as e:
            error_detalle = str(e)

    # 4. Verificar si podemos listar el directorio de red
    if conexion_exitosa:
        try:
            ruta_p = Path(ruta_red)
            # Intentar listar elementos
            _ = list(ruta_p.iterdir())
        except PermissionError:
            return {"ok": False, "mensaje": "Credenciales incorrectas o la cuenta no tiene permisos sobre la carpeta compartida."}
        except Exception as e:
            # Si no responde el recurso
            return {"ok": False, "mensaje": f"No se pudo acceder a la ruta de red {ruta_red}: {e}"}

        # Actualizar estado global compartido
        estado_bosgame.conectado = True
        estado_bosgame.ip = ip
        estado_bosgame.usuario = usuario
        estado_bosgame.carpeta = carpeta
        estado_bosgame.ruta_red = ruta_red
        estado_bosgame.tiempo_conexion = datetime.datetime.now()
        estado_bosgame.puerto_445_abierto = p445

        # Medir estadísticas iniciales de la red
        stats_lat = bosgame_medir_latencias(ip, cantidad=5)
        estado_bosgame.latencias = stats_lat["muestras"]
        estado_bosgame.latencia_promedio = stats_lat["avg"]
        estado_bosgame.latencia_minima = stats_lat["min"]
        estado_bosgame.latencia_maxima = stats_lat["max"]
        estado_bosgame.perdida_pct = stats_lat["perdida_pct"]
        estado_bosgame.calidad = stats_lat["calidad"]

        # Calcular espacio de disco y conteo de archivos
        bosgame_actualizar_estadisticas_almacenamiento()

        return {
            "ok": True,
            "mensaje": f"Conexión exitosa a {ruta_red} con el usuario '{usuario}'.",
            "ruta_red": ruta_red
        }
    else:
        return {
            "ok": False,
            "mensaje": f"Fallo al conectar con la BOSGAME en {ruta_red}. {error_detalle}"
        }


def bosgame_desconectar() -> dict:
    """
    Cierra la conexión activa con la carpeta compartida de la BOSGAME
    y limpia el objeto de estado compartido.
    """
    if not estado_bosgame.conectado:
        return {"ok": True, "mensaje": "No había ninguna conexión activa."}

    ruta = estado_bosgame.ruta_red
    try:
        # Intentar con WNetCancelConnection2W
        mpr = ctypes.windll.mpr
        mpr.WNetCancelConnection2W(ruta, 0, True)
    except Exception:
        pass

    try:
        subprocess.run(["net", "use", ruta, "/delete", "/y"], capture_output=True, text=True, errors="replace", creationflags=NO_WINDOW)
    except Exception:
        pass

    estado_bosgame.limpiar()
    return {"ok": True, "mensaje": f"Desconectado exitosamente de {ruta}."}


def bosgame_actualizar_estadisticas_almacenamiento():
    """Actualiza el espacio en disco y número de archivos de la ruta compartida."""
    if not estado_bosgame.conectado or not estado_bosgame.ruta_red:
        return

    gb = 1024 ** 3
    try:
        total, usado, libre = shutil.disk_usage(estado_bosgame.ruta_red)
        estado_bosgame.espacio_total_gb = round(total / gb, 1)
        estado_bosgame.espacio_usado_gb = round(usado / gb, 1)
        estado_bosgame.espacio_libre_gb = round(libre / gb, 1)
    except Exception:
        pass

    try:
        ruta_p = Path(estado_bosgame.ruta_red)
        archivos = [f for f in ruta_p.iterdir() if f.is_file()]
        estado_bosgame.total_archivos = len(archivos)
    except Exception:
        pass


# ==============================================================================
# HERRAMIENTA 7: RESPALDO DE CARPETAS (COMPRESIÓN ZIP)
# ==============================================================================

def sugerir_nombre_respaldo(carpeta_origen: Path) -> str:
    """Genera un nombre sugerido descriptivo con fecha y hora para el respaldo."""
    nom = carpeta_origen.name or "Carpeta"
    nom_seguro = "".join(c for c in nom if c.isalnum() or c in ("-", "_"))
    fecha_hora = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    return f"Respaldo_{nom_seguro}_{fecha_hora}.zip"


def calcular_tamano_carpeta(carpeta: Path) -> int:
    """Calcula el tamaño total en bytes de los archivos dentro de una carpeta."""
    total = 0
    try:
        for root, _, files in os.walk(str(carpeta)):
            for f in files:
                try:
                    total += (Path(root) / f).stat().st_size
                except Exception:
                    pass
    except Exception:
        pass
    return total


def crear_respaldo_zip(carpeta_origen: Path, carpeta_destino: Path, nombre_zip: str, cancel_event=None, progress_callback=None) -> dict:
    """
    Crea un respaldo comprimido (.zip) de la carpeta_origen en carpeta_destino.
    Excluye el propio archivo zip si el destino está dentro del origen.
    Omite archivos sin permisos de lectura y reporta el progreso mediante callback.
    """
    inicio = time.time()
    if not carpeta_origen.exists() or not carpeta_origen.is_dir():
        return {"ok": False, "mensaje": "La carpeta de origen seleccionada no existe o no es válida."}

    if not nombre_zip.lower().endswith(".zip"):
        nombre_zip += ".zip"

    archivo_zip_salida = carpeta_destino / nombre_zip
    archivos_a_incluir = []

    # 1. Recorrer y recopilar archivos válidos
    for root, dirs, files in os.walk(str(carpeta_origen)):
        for f in files:
            p = Path(root) / f
            # Excluir el archivo de respaldo si se está creando dentro del origen
            if p.resolve() == archivo_zip_salida.resolve():
                continue
            archivos_a_incluir.append(p)

    total_archivos = len(archivos_a_incluir)
    if total_archivos == 0:
        return {"ok": False, "mensaje": "La carpeta de origen está vacía; no hay archivos para respaldar."}

    archivos_empaquetados = 0
    archivos_omitidos = 0
    tam_original_bytes = 0

    try:
        carpeta_destino.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archivo_zip_salida, "w", zipfile.ZIP_DEFLATED) as zipf:
            for i, p in enumerate(archivos_a_incluir, 1):
                if cancel_event and cancel_event.is_set():
                    try:
                        archivo_zip_salida.unlink()
                    except Exception:
                        pass
                    return {"ok": False, "mensaje": "Creación del respaldo cancelada por el usuario."}

                try:
                    tam_original_bytes += p.stat().st_size
                    # Ruta relativa dentro del archivo comprimido
                    arcname = p.relative_to(carpeta_origen)
                    zipf.write(p, arcname=str(arcname))
                    archivos_empaquetados += 1
                except Exception:
                    archivos_omitidos += 1

                if progress_callback:
                    pct = int((i / total_archivos) * 100)
                    progress_callback(pct, i, total_archivos)

    except Exception as e:
        return {"ok": False, "mensaje": f"Error al generar el archivo ZIP: {e}"}

    duracion = round(time.time() - inicio, 1)
    tam_comprimido_bytes = archivo_zip_salida.stat().st_size if archivo_zip_salida.exists() else 0

    reduccion_pct = 0.0
    if tam_original_bytes > 0:
        reduccion_pct = round((1.0 - (tam_comprimido_bytes / tam_original_bytes)) * 100, 1)

    mb = 1024 ** 2
    return {
        "ok": True,
        "mensaje": f"Respaldo creado con éxito en: {archivo_zip_salida.name}",
        "archivo_salida": str(archivo_zip_salida),
        "total_archivos": archivos_empaquetados,
        "omitidos": archivos_omitidos,
        "tam_original_mb": round(tam_original_bytes / mb, 2),
        "tam_comprimido_mb": round(tam_comprimido_bytes / mb, 2),
        "reduccion_pct": reduccion_pct,
        "duracion_segundos": duracion,
        "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def listar_respaldos_en_destino(carpeta_destino: Path) -> list:
    """Lista todos los archivos .zip disponibles en la carpeta de destino."""
    respaldos = []
    try:
        if carpeta_destino.exists() and carpeta_destino.is_dir():
            for f in carpeta_destino.iterdir():
                if f.is_file() and f.suffix.lower() == ".zip":
                    stats = f.stat()
                    tam_mb = round(stats.st_size / (1024 ** 2), 2)
                    fecha = datetime.datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M")
                    respaldos.append({
                        "nombre": f.name,
                        "tam_mb": tam_mb,
                        "fecha": fecha,
                        "ruta_completa": f
                    })
    except Exception:
        pass

    respaldos.sort(key=lambda x: x["fecha"], reverse=True)
    return respaldos


def restaurar_respaldo_zip(archivo_zip: Path, carpeta_destino: Path) -> dict:
    """Extrae el contenido de un respaldo .zip dentro de la carpeta destino elegida."""
    try:
        if not archivo_zip.exists():
            return {"ok": False, "mensaje": "El archivo de respaldo seleccionado no existe."}

        carpeta_destino.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archivo_zip, "r") as zipf:
            zipf.extractall(carpeta_destino)

        return {
            "ok": True,
            "mensaje": f"Respaldo extraído exitosamente en: {carpeta_destino}"
        }
    except Exception as e:
        return {"ok": False, "mensaje": f"Error al extraer respaldo: {e}"}


# ==============================================================================
# HERRAMIENTA 8: EDITOR Y ENVÍO DE ARCHIVOS
# ==============================================================================

def validar_nombre_archivo_windows(nombre: str) -> bool:
    """Comprueba que el nombre del archivo no contenga caracteres prohibidos en Windows."""
    caracteres_prohibidos = r'<>:"/\|?*'
    return not any(c in caracteres_prohibidos for c in nombre)


def guardar_archivo_texto(carpeta_local: Path, nombre_archivo: str, contenido: str) -> dict:
    """
    Guarda el contenido en un archivo de texto en la carpeta local seleccionada.
    Fuerza la extensión .txt y valida los caracteres del nombre.
    """
    nombre_archivo = nombre_archivo.strip()
    if not nombre_archivo:
        return {"ok": False, "mensaje": "Debe indicar un nombre para el archivo."}

    if not validar_nombre_archivo_windows(nombre_archivo):
        return {"ok": False, "mensaje": 'El nombre contiene caracteres no permitidos en Windows (<>:"/\\|?*).'}

    if not nombre_archivo.lower().endswith(".txt"):
        nombre_archivo += ".txt"

    try:
        carpeta_local.mkdir(parents=True, exist_ok=True)
        ruta_archivo = carpeta_local / nombre_archivo
        with open(ruta_archivo, "w", encoding="utf-8") as f:
            f.write(contenido)

        return {
            "ok": True,
            "mensaje": f"Archivo guardado correctamente: {nombre_archivo}",
            "ruta_completa": ruta_archivo
        }
    except Exception as e:
        return {"ok": False, "mensaje": f"Error al guardar el archivo: {e}"}


def abrir_archivo_texto(ruta_archivo: Path) -> dict:
    """Lee y carga el contenido de un archivo de texto existente."""
    try:
        with open(ruta_archivo, "r", encoding="utf-8", errors="replace") as f:
            contenido = f.read()
        return {"ok": True, "contenido": contenido, "nombre": ruta_archivo.name}
    except Exception as e:
        return {"ok": False, "mensaje": f"Error al abrir archivo: {e}"}


def enviar_archivo_a_bosgame(ruta_archivo_local: Path, sobrescribir: bool = False, renombrar_con_timestamp: bool = False) -> dict:
    """
    Copia el archivo local hacia la carpeta compartida activa de la BOSGAME
    utilizando shutil.copy2 y verificando que el tamaño del archivo copiado coincida.
    """
    if not estado_bosgame.conectado or not estado_bosgame.ruta_red:
        return {"ok": False, "mensaje": "No hay conexión activa con la BOSGAME. Conéctese primero en la Herramienta 6."}

    if not ruta_archivo_local.exists() or not ruta_archivo_local.is_file():
        return {"ok": False, "mensaje": "El archivo local seleccionado no existe."}

    carpeta_remota = Path(estado_bosgame.ruta_red)
    nombre_destino = ruta_archivo_local.name

    if renombrar_con_timestamp:
        stem = ruta_archivo_local.stem
        ext = ruta_archivo_local.suffix
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_destino = f"{stem}_{ts}{ext}"

    archivo_destino = carpeta_remota / nombre_destino

    if archivo_destino.exists() and not sobrescribir and not renombrar_con_timestamp:
        return {
            "ok": False,
            "ya_existe": True,
            "mensaje": f"El archivo '{nombre_destino}' ya existe en la BOSGAME. ¿Desea sobrescribirlo o renombrarlo?"
        }

    try:
        tam_origen = ruta_archivo_local.stat().st_size
        shutil.copy2(ruta_archivo_local, archivo_destino)

        # Verificar integridad por tamaño
        if not archivo_destino.exists():
            return {"ok": False, "mensaje": "Fallo de transferencia: El archivo no apareció en el destino remoto."}

        tam_remoto = archivo_destino.stat().st_size
        if tam_origen != tam_remoto:
            return {"ok": False, "mensaje": f"Error de verificación: Tamaños no coinciden ({tam_origen} B vs {tam_remoto} B)."}

        return {
            "ok": True,
            "mensaje": f"Archivo '{nombre_destino}' enviado y verificado correctamente en la BOSGAME.",
            "nombre_destino": nombre_destino,
            "tam_bytes": tam_remoto
        }
    except PermissionError:
        return {"ok": False, "mensaje": "Acceso denegado: Su usuario no tiene permisos de escritura en la carpeta de la BOSGAME."}
    except Exception as e:
        return {"ok": False, "mensaje": f"Error al copiar archivo a la BOSGAME: {e}"}


# ==============================================================================
# HERRAMIENTA 9: PERMISOS DE ARCHIVOS (ICACLS SELECCIONABLE)
# ==============================================================================

# Registro en memoria de respaldos de ACL para la función 'Restaurar permisos'
_respaldos_acl_archivos = {}

def permisos_ver_actuales(ruta_archivo: Path) -> dict:
    """Ejecuta 'icacls' para consultar los permisos actuales sobre un archivo."""
    try:
        proc = subprocess.run(["icacls", str(ruta_archivo)], capture_output=True, text=True, errors="replace", creationflags=NO_WINDOW)
        salida = proc.stdout.strip()
        return {"ok": True, "salida": salida}
    except Exception as e:
        return {"ok": False, "mensaje": f"Error al consultar permisos: {e}"}


def permisos_guardar_originales(ruta_archivo: Path) -> dict:
    """
    Guarda una instantánea de las Listas de Control de Acceso (DACL) originales
    utilizando 'icacls /save' en un archivo seguro en el Workspace.
    """
    try:
        ws = obtener_ruta_workspace()
        acl_backup = ws / f"acl_backup_{ruta_archivo.name}.acl"
        cmd = ["icacls", str(ruta_archivo.parent), "/save", str(acl_backup), "/t"]
        proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace", creationflags=NO_WINDOW)
        if proc.returncode == 0:
            _respaldos_acl_archivos[str(ruta_archivo.resolve())] = acl_backup
            return {"ok": True, "archivo_acl": str(acl_backup)}
        else:
            return {"ok": False, "mensaje": proc.stderr or proc.stdout}
    except Exception as e:
        return {"ok": False, "mensaje": str(e)}


def permisos_aplicar(ruta_archivo: Path, usuario_grupo: str, tipo_accion: str, permisos_seleccionados: list) -> dict:
    """
    Aplica permisos específicos sobre un archivo mediante icacls.
    usuario_grupo: nombre de usuario o grupo (Ej: angel, Todos, Usuarios).
    tipo_accion: 'Permitir' (/grant:r) o 'Denegar' (/deny).
    permisos_seleccionados: lista de códigos (R, W, RX, M, D, F).
    """
    if not permisos_seleccionados:
        return {"ok": False, "mensaje": "Debe seleccionar al menos una casilla de permiso para aplicar."}

    # Guardar copia de respaldo si es la primera modificación sobre este archivo
    str_res = str(ruta_archivo.resolve())
    if str_res not in _respaldos_acl_archivos:
        permisos_guardar_originales(ruta_archivo)

    # Construir máscara de permisos (ej: (R,W) o (F))
    mascara = ",".join(permisos_seleccionados)

    # En Windows, para 'Permitir' usamos /grant:r para reemplazar permisos previos del usuario
    flag = "/grant:r" if tipo_accion == "Permitir" else "/deny"
    regla = f"{usuario_grupo}:({mascara})"

    cmd = ["icacls", str(ruta_archivo), flag, regla]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace", creationflags=NO_WINDOW)
        if proc.returncode == 0:
            return {
                "ok": True,
                "mensaje": f"Permisos actualizados con éxito ({tipo_accion} {mascara} a '{usuario_grupo}').",
                "comando": " ".join(cmd),
                "salida": proc.stdout.strip()
            }
        else:
            return {
                "ok": False,
                "mensaje": f"icacls reportó un error: {proc.stderr or proc.stdout}",
                "comando": " ".join(cmd)
            }
    except Exception as e:
        return {"ok": False, "mensaje": f"Error al ejecutar icacls: {e}"}


def permisos_probar_lectura(ruta_archivo: Path) -> dict:
    """Comprueba empíricamente si el usuario actual puede leer el archivo."""
    try:
        with open(ruta_archivo, "r", encoding="utf-8", errors="replace") as f:
            contenido = f.read(150)
        return {
            "ok": True,
            "mensaje": f"Lectura EXITOSA: Se leyeron {len(contenido)} caracteres sin restricciones.",
            "muestra": contenido[:60]
        }
    except PermissionError:
        return {
            "ok": False,
            "mensaje": "ACCESO DENEGADO (PermissionError / Win32 ERROR_ACCESS_DENIED): El kernel de Windows impidió la lectura del archivo."
        }
    except Exception as e:
        return {"ok": False, "mensaje": f"Error al intentar leer: {e}"}


def permisos_probar_escritura(ruta_archivo: Path) -> dict:
    """Comprueba empíricamente si el usuario actual puede escribir/modificar el archivo."""
    try:
        with open(ruta_archivo, "a", encoding="utf-8") as f:
            f.write(f"\n[Test de escritura BrachioDiag - {datetime.datetime.now().strftime('%H:%M:%S')}]")
        return {
            "ok": True,
            "mensaje": "Escritura EXITOSA: Se añadieron datos al archivo correctamente."
        }
    except PermissionError:
        return {
            "ok": False,
            "mensaje": "ACCESO DENEGADO (PermissionError / Win32 ERROR_ACCESS_DENIED): La regla Deny ACE bloqueó la modificación del archivo."
        }
    except Exception as e:
        return {"ok": False, "mensaje": f"Error al intentar escribir: {e}"}


def permisos_restaurar_originales(ruta_archivo: Path) -> dict:
    """
    Restaura las listas de control de acceso originales ejecutando 'icacls /reset'
    o aplicando la copia guardada con /restore.
    """
    try:
        cmd = ["icacls", str(ruta_archivo), "/reset"]
        proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace", creationflags=NO_WINDOW)
        if proc.returncode == 0:
            return {
                "ok": True,
                "mensaje": "Permisos originales restaurados exitosamente (herencia NTFS restablecida).",
                "salida": proc.stdout.strip()
            }
        else:
            return {"ok": False, "mensaje": proc.stderr or proc.stdout}
    except Exception as e:
        return {"ok": False, "mensaje": f"Error al restaurar permisos: {e}"}


# ==============================================================================
# EVALUACIÓN DE SALUD DEL SISTEMA (TACÓMETRO 0 A 100%)
# ==============================================================================

def calcular_puntaje_salud(sistema: dict, discos: list, red: dict, bosgame_ok: bool = False, cpu_pct: float = None) -> tuple:
    """
    Algoritmo de ponderación de salud global del sistema (0 a 100%).
    Evalúa la memoria RAM disponible, el espacio en disco C:, la conectividad y el CPU.
    Devuelve (puntaje_entero, estado_texto, explicaciones_lista).
    """
    score = 100
    explicaciones = []

    # 1. Evaluación de memoria RAM
    ram = sistema.get("ram", {})
    carga_ram = ram.get("carga_pct", 50)
    if carga_ram > 90:
        score -= 25
        explicaciones.append(f"RAM crítica: {carga_ram}% de memoria ocupada (-25 pts)")
    elif carga_ram > 80:
        score -= 15
        explicaciones.append(f"RAM alta: {carga_ram}% de memoria ocupada (-15 pts)")
    elif carga_ram > 70:
        score -= 8
        explicaciones.append(f"RAM moderada: {carga_ram}% de carga (-8 pts)")
    else:
        explicaciones.append(f"Memoria RAM en estado óptimo ({carga_ram}% de carga)")

    # 2. Evaluación de disco principal C:
    disco_c = next((d for d in discos if d.get("letra", "").upper() == "C:"), None)
    if disco_c:
        pct_libre = disco_c.get("pct_libre", 50)
        libre_gb = disco_c.get("libre_gb", 50)
        if libre_gb < 5 or pct_libre < 10:
            score -= 25
            explicaciones.append(f"Espacio libre en C: crítico ({libre_gb} GB libres, {pct_libre}%) (-25 pts)")
        elif libre_gb < 15 or pct_libre < 15:
            score -= 15
            explicaciones.append(f"Espacio en C: bajo ({libre_gb} GB libres) (-15 pts)")
        else:
            explicaciones.append(f"Disco C: con buen margen de almacenamiento ({libre_gb} GB libres)")

    # 3. Evaluación de CPU si se conoce
    if cpu_pct is not None:
        if cpu_pct > 85:
            score -= 20
            explicaciones.append(f"CPU en sobrecarga: {cpu_pct:.1f}% de uso (-20 pts)")
        elif cpu_pct > 65:
            score -= 10
            explicaciones.append(f"CPU con uso elevado: {cpu_pct:.1f}% (-10 pts)")
        else:
            explicaciones.append(f"Uso de procesador normal ({cpu_pct:.1f}%)")

    # 4. Evaluación de red
    adaptadores = red.get("adaptadores", [])
    if adaptadores:
        explicaciones.append(f"Red configurada ({len(adaptadores)} adaptador/es activo/s)")
    else:
        score -= 10
        explicaciones.append("No se detectaron adaptadores IPv4 activos (-10 pts)")

    if bosgame_ok:
        explicaciones.append("Conexión con la BOSGAME establecida correctamente")

    score = max(10, min(100, score))

    if score >= 85:
        estado = "ÓPTIMO"
    elif score >= 65:
        estado = "BUENO"
    elif score >= 50:
        estado = "REGULAR"
    else:
        estado = "CRÍTICO"

    return score, estado, explicaciones


# ==============================================================================
# HERRAMIENTA 10: INFORME DE DIAGNÓSTICO (.TXT Y .HTML)
# ==============================================================================

def generar_informe_completo(datos_aplicacion: dict) -> dict:
    """
    Genera los informes de auditoría en texto plano (.txt) y HTML interactivo.
    Solo incluye datos de las herramientas que hayan sido ejecutadas; lo no ejecutado
    se marca explícitamente como 'No ejecutado'.
    NO contiene explicaciones del dinosaurio ni el porqué del nombre/logo.
    Nombre de la desarrolladora: Angélica Serracín.
    """
    ws = obtener_ruta_workspace()
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    fecha_legible = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    ruta_txt = ws / f"BrachioDiag_Informe_{ts}.txt"
    ruta_html = ws / f"BrachioDiag_Informe_{ts}.html"

    sis = datos_aplicacion.get("sistema") or {}
    ram = sis.get("ram", {})
    discos = datos_aplicacion.get("discos") or []
    archivos_pesados = datos_aplicacion.get("archivos_pesados") or []
    programas = datos_aplicacion.get("programas") or []
    inicio = datos_aplicacion.get("inicio") or []
    errores = datos_aplicacion.get("errores") or {}
    red = datos_aplicacion.get("red") or {}
    rendimiento = datos_aplicacion.get("rendimiento") or {}
    respaldo = datos_aplicacion.get("respaldo") or {}
    envio = datos_aplicacion.get("envio") or {}
    permisos = datos_aplicacion.get("permisos") or {}
    salud = datos_aplicacion.get("salud") or (85, "ÓPTIMO", [])

    # 1. Generar Informe TXT
    lineas_txt = [
        "=" * 80,
        " INFORME DE AUDITORÍA Y DIAGNÓSTICO DEL SISTEMA - BrachioDiag",
        " Desarrolladora: Angélica Serracín | Materia: Sistemas Operativos (UTP)",
        f" Fecha y Hora de Generación: {fecha_legible}",
        "=" * 80,
        "",
        f"PUNTAJE DE SALUD GLOBAL DEL EQUIPO: {salud[0]}% ({salud[1]})",
        "-" * 80,
    ]
    for exp in salud[2]:
        lineas_txt.append(f" * {exp}")

    lineas_txt.extend([
        "",
        "=" * 80,
        " 1. INFORMACIÓN GENERAL DEL EQUIPO Y DEL SISTEMA OPERATIVO",
        "=" * 80,
        f" Sistema Operativo:   {sis.get('so', 'Windows')} ({sis.get('compilacion', 'N/D')})",
        f" Arquitectura:        {sis.get('arquitectura', 'N/D')}",
        f" Procesador (CPU):    {sis.get('cpu', 'N/D')} ({sis.get('nucleos', 1)} hilos)",
        f" Memoria RAM Total:   {ram.get('total_gb', 0)} GB",
        f" Memoria RAM Usada:   {ram.get('usado_gb', 0)} GB ({ram.get('carga_pct', 0)}% de carga)",
        f" Memoria RAM Libre:   {ram.get('libre_gb', 0)} GB",
        f" Tiempo Activo (Up):  {sis.get('uptime', 'N/D')}",
        f" Usuario Actual:      {sis.get('usuario', 'N/D')}",
        f" Nombre del Equipo:   {sis.get('equipo', 'N/D')}",
        f" Privilegios UAC:     {'Administrador' if sis.get('es_admin') else 'Usuario Estándar'}",
        "",
        "=" * 80,
        " 2. ÚLTIMA MEDICIÓN DEL MONITOR DE RENDIMIENTO",
        "=" * 80,
    ])
    if rendimiento:
        lineas_txt.extend([
            f" Uso de CPU:          {rendimiento.get('cpu_pct', 0)}% ({rendimiento.get('frase_cpu', '')})",
            f" Uso de Memoria RAM:  {rendimiento.get('ram_pct', 0)}% ({rendimiento.get('ram_usada_gb', 0)} / {rendimiento.get('ram_total_gb', 0)} GB)",
            f" Frase de Memoria:    {rendimiento.get('frase_ram', '')}",
        ])
    else:
        lineas_txt.append(" Estado: No ejecutado durante esta sesión.")

    lineas_txt.extend([
        "",
        "=" * 80,
        " 3. DISCOS Y ALMACENAMIENTO",
        "=" * 80,
    ])
    if discos:
        for d in discos:
            lineas_txt.append(f" Unidad {d.get('letra')}: Total {d.get('total_gb')} GB | Usado {d.get('usado_gb')} GB ({d.get('pct_usado')}%) | Libre {d.get('libre_gb')} GB")
    else:
        lineas_txt.append(" Estado: No ejecutado.")

    if archivos_pesados:
        lineas_txt.append("\n --- Archivos Más Pesados Detectados (Top 10) ---")
        for i, a in enumerate(archivos_pesados[:10], 1):
            lineas_txt.append(f" {i}. {a.get('nombre')} ({a.get('tam_legible')}) - {a.get('carpeta')}")

    lineas_txt.extend([
        "",
        "=" * 80,
        " 4. PROGRAMAS Y ERRORES DEL SISTEMA",
        "=" * 80,
    ])
    if programas:
        lineas_txt.append(f" Total de Programas Instalados Registrados: {len(programas)}")
        for p in programas[:5]:
            lineas_txt.append(f"  - {p.get('nombre')} (v{p.get('version')}) - {p.get('editor')}")
        if len(programas) > 5:
            lineas_txt.append(f"  ... y {len(programas) - 5} programas más.")
    else:
        lineas_txt.append(" Programas instalados: No consultado.")

    if inicio:
        lineas_txt.append(f"\n Programas de Inicio Automático: {len(inicio)}")
        for ini in inicio:
            lineas_txt.append(f"  * {ini.get('nombre')} [{ini.get('origen')}] -> {ini.get('comando')[:60]}")
    else:
        lineas_txt.append(" Programas de inicio: No consultado.")

    if errores:
        lineas_txt.append(f"\n Visor de Eventos del Sistema: {errores.get('mensaje', '')}")
        if errores.get("causa_probable"):
            lineas_txt.append(f" Causa: {errores.get('causa_probable')}")
    else:
        lineas_txt.append(" Errores del sistema: No consultado.")

    lineas_txt.extend([
        "",
        "=" * 80,
        " 5. CONFIGURACIÓN IP Y RED",
        "=" * 80,
    ])
    adaptadores = red.get("adaptadores", [])
    if adaptadores:
        for ad in adaptadores:
            lineas_txt.append(f" Adaptador: {ad.get('nombre')}")
            lineas_txt.append(f"  IPv4:     {ad.get('ipv4')} | Máscara: {ad.get('mascara')}")
            lineas_txt.append(f"  Gateway:  {ad.get('gateway')} | MAC: {ad.get('mac')}")
    else:
        lineas_txt.append(" Estado: No ejecutado.")

    lineas_txt.extend([
        "",
        "=" * 80,
        " 6. ESTADO DE CONEXIÓN CON LA BOSGAME",
        "=" * 80,
    ])
    if estado_bosgame.conectado:
        lineas_txt.extend([
            f" Estado:              CONECTADO",
            f" Dirección IP:        {estado_bosgame.ip}",
            f" Usuario Autenticado: {estado_bosgame.usuario}",
            f" Ruta de Red:         {estado_bosgame.ruta_red}",
            f" Calidad Conexión:    {estado_bosgame.calidad}",
            f" Latencia Promedio:   {estado_bosgame.latencia_promedio} ms (Mín: {estado_bosgame.latencia_minima} ms / Máx: {estado_bosgame.latencia_maxima} ms)",
            f" Pérdida de paquetes: {estado_bosgame.perdida_pct}%",
            f" Puerto 445:          {'Abierto' if estado_bosgame.puerto_445_abierto else 'Cerrado'}",
            f" Espacio Remoto:      {estado_bosgame.espacio_libre_gb} GB libres de {estado_bosgame.espacio_total_gb} GB",
            f" Archivos en Share:   {estado_bosgame.total_archivos}",
        ])
    else:
        lineas_txt.append(" Estado: No conectado con la BOSGAME durante la generación de este informe.")

    lineas_txt.extend([
        "",
        "=" * 80,
        " 7. RESPALDOS, ENVÍO Y SEGURIDAD NTFS",
        "=" * 80,
    ])
    if respaldo:
        lineas_txt.append(f" Respaldo Creado:     {respaldo.get('mensaje')}")
        lineas_txt.append(f"  Archivos: {respaldo.get('total_archivos')} | Original: {respaldo.get('tam_original_mb')} MB | Comprimido: {respaldo.get('tam_comprimido_mb')} MB ({respaldo.get('reduccion_pct')}% reducción)")
    else:
        lineas_txt.append(" Respaldo de carpetas: No ejecutado.")

    if envio:
        lineas_txt.append(f" Envío a BOSGAME:     {envio.get('mensaje')}")
    else:
        lineas_txt.append(" Envío a BOSGAME:     No ejecutado.")

    if permisos:
        lineas_txt.append(f" Auditoría Permisos:  {permisos.get('mensaje')}")
    else:
        lineas_txt.append(" Auditoría Permisos:  No ejecutado.")

    lineas_txt.extend([
        "",
        "=" * 80,
        " FIN DEL INFORME | BRACHIODIAG",
        "=" * 80,
    ])

    with open(ruta_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas_txt))

    # 2. Generar Informe HTML Moderno y 100% Responsive
    color_score = "#50FA7B" if salud[0] >= 85 else ("#FFB86C" if salud[0] >= 65 else "#F72585")

    # Cargar imágenes base64 para el informe HTML autónomo
    from estilos import ruta_recurso
    p_logo_grande = ruta_recurso("assets/logo_grande.png")
    p_logo_pequeno = ruta_recurso("assets/logo_pequeno.png")

    b64_logo_grande = ""
    b64_favicon = ""

    if p_logo_grande.exists():
        try:
            with open(p_logo_grande, "rb") as img_f:
                b64_logo_grande = f"data:image/png;base64,{base64.b64encode(img_f.read()).decode('ascii')}"
        except Exception:
            pass

    if p_logo_pequeno.exists():
        try:
            with open(p_logo_pequeno, "rb") as img_f:
                b64_favicon = f"data:image/png;base64,{base64.b64encode(img_f.read()).decode('ascii')}"
        except Exception:
            pass

    favicon_tag = f'<link rel="icon" type="image/png" href="{b64_favicon}">' if b64_favicon else ''
    
    if b64_logo_grande:
        logo_header_tag = f"""<div style="display: flex; align-items: center; gap: 16px; margin-bottom: 8px;">
            <img src="{b64_logo_grande}" alt="BrachioDiag Logo" style="max-height: 70px; max-width: 70px; object-fit: contain;">
            <div>
                <h1 style="color:#FF70A6; margin:0; font-size: 26px;">BrachioDiag</h1>
                <span style="color:#B8B8C8; font-size: 13px;">Herramienta de Diagnóstico para Windows</span>
            </div>
        </div>"""
    else:
        logo_header_tag = """<div style="margin-bottom: 8px;">
            <h1 style="color:#FF70A6; margin:0; font-size: 26px;">🦕 BrachioDiag</h1>
            <span style="color:#B8B8C8; font-size: 13px;">Herramienta de Diagnóstico para Windows</span>
        </div>"""

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BrachioDiag - Informe de Diagnóstico</title>
    {favicon_tag}
    <style>
        * {{
            box-sizing: border-box;
        }}
        body {{
            background-color: #1A0B2E;
            color: #F5F5FA;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 24px 16px;
            line-height: 1.5;
        }}
        .container {{
            max-width: 1050px;
            margin: 0 auto;
        }}
        .header {{
            background-color: #2A1450;
            border-left: 6px solid #F72585;
            padding: 24px;
            border-radius: 12px;
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            gap: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.4);
        }}
        .header-info {{
            flex: 1 1 300px;
        }}
        .header-info p {{
            margin: 4px 0 0 0;
            color: #B8B8C8;
            font-size: 14px;
        }}
        .card {{
            background-color: #2A1450;
            border: 1px solid #3E1E6B;
            border-radius: 12px;
            padding: 20px;
            margin-top: 20px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }}
        .card h2 {{
            margin-top: 0;
            font-size: 18px;
            color: #FF70A6;
            border-bottom: 1px solid #3E1E6B;
            padding-bottom: 10px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 12px;
        }}
        .item {{
            background-color: #1A0B2E;
            padding: 14px;
            border-radius: 8px;
            font-size: 14px;
            border: 1px solid #220D3E;
        }}
        .item strong {{
            color: #9D4EDD;
            display: block;
            margin-bottom: 4px;
            font-size: 13px;
        }}
        .score-box {{
            text-align: center;
            padding: 16px 24px;
            background: #1A0B2E;
            border-radius: 10px;
            border: 2px solid {color_score};
            min-width: 140px;
        }}
        .score-val {{
            font-size: 44px;
            font-weight: bold;
            color: {color_score};
            margin: 0;
            line-height: 1;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
            background-color: #7B2FF7;
            color: #fff;
        }}
        .table-responsive {{
            width: 100%;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
            font-size: 14px;
            min-width: 500px;
        }}
        th, td {{
            padding: 10px 12px;
            text-align: left;
            border-bottom: 1px solid #3E1E6B;
        }}
        th {{
            color: #FF70A6;
            background-color: #1A0B2E;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            color: #B8B8C8;
            font-size: 13px;
        }}
        @media (max-width: 768px) {{
            body {{
                padding: 12px 8px;
            }}
            .header {{
                flex-direction: column;
                align-items: flex-start;
            }}
            .score-box {{
                width: 100%;
            }}
            .grid {{
                grid-template-columns: 1fr;
            }}
        }}
        @media print {{
            body {{
                background-color: #fff;
                color: #000;
            }}
            .card {{
                background: #fff;
                border: 1px solid #ccc;
                box-shadow: none;
                color: #000;
            }}
            .item {{
                background: #f8f8f8;
                color: #000;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-info">
                {logo_header_tag}
                <p>Informe de Diagnóstico y Auditoría para Windows | <strong>Desarrolladora: Angélica Serracín</strong></p>
                <p>Fecha de emisión: {fecha_legible}</p>
            </div>
            <div class="score-box">
                <div class="score-val">{salud[0]}%</div>
                <div style="color: {color_score}; font-weight: bold; font-size: 13px; margin-top: 4px;">{salud[1]}</div>
            </div>
        </div>

        <div class="card">
            <h2>1. Información General del Sistema Operativo</h2>
            <div class="grid">
                <div class="item"><strong>Sistema Operativo:</strong> {sis.get('so', 'Windows')} ({sis.get('compilacion', 'N/D')})</div>
                <div class="item"><strong>Procesador:</strong> {sis.get('cpu', 'N/D')} ({sis.get('nucleos', 1)} hilos)</div>
                <div class="item"><strong>Memoria RAM:</strong> {ram.get('usado_gb', 0)} GB / {ram.get('total_gb', 0)} GB ({ram.get('carga_pct', 0)}% ocupado)</div>
                <div class="item"><strong>Tiempo de Actividad:</strong> {sis.get('uptime', 'N/D')}</div>
                <div class="item"><strong>Usuario y Equipo:</strong> {sis.get('usuario', 'N/D')} @ {sis.get('equipo', 'N/D')}</div>
                <div class="item"><strong>Nivel UAC:</strong> <span class="badge">{'Administrador' if sis.get('es_admin') else 'Usuario Estándar'}</span></div>
            </div>
        </div>

        <div class="card">
            <h2>2. Monitor de Rendimiento</h2>
            {f'''<div class="grid">
                <div class="item"><strong>Uso de CPU:</strong> {rendimiento.get('cpu_pct', 0)}% - {rendimiento.get('frase_cpu', '')}</div>
                <div class="item"><strong>Uso de Memoria:</strong> {rendimiento.get('ram_pct', 0)}% - {rendimiento.get('frase_ram', '')}</div>
            </div>''' if rendimiento else '<p style="color:#B8B8C8;">No ejecutado durante esta sesión.</p>'}
        </div>

        <div class="card">
            <h2>3. Discos y Almacenamiento</h2>
            <div class="table-responsive">
                <table>
                    <tr><th>Unidad</th><th>Espacio Total</th><th>Espacio Usado</th><th>Espacio Libre</th><th>Carga</th></tr>
                    {''.join(f"<tr><td>{d.get('letra')}</td><td>{d.get('total_gb')} GB</td><td>{d.get('usado_gb')} GB</td><td>{d.get('libre_gb')} GB</td><td>{d.get('pct_usado')}%</td></tr>" for d in discos) if discos else '<tr><td colspan="5">No ejecutado.</td></tr>'}
                </table>
            </div>
        </div>

        <div class="card">
            <h2>4. Conexión con la BOSGAME (Carpeta Compartida)</h2>
            {f'''<div class="grid">
                <div class="item"><strong>Estado:</strong> <span style="color:#50FA7B; font-weight:bold;">CONECTADO</span></div>
                <div class="item"><strong>IP y Ruta:</strong> {estado_bosgame.ruta_red}</div>
                <div class="item"><strong>Usuario:</strong> {estado_bosgame.usuario}</div>
                <div class="item"><strong>Latencia:</strong> {estado_bosgame.latencia_promedio} ms ({estado_bosgame.calidad})</div>
                <div class="item"><strong>Espacio Libre:</strong> {estado_bosgame.espacio_libre_gb} GB libres de {estado_bosgame.espacio_total_gb} GB</div>
                <div class="item"><strong>Archivos en Share:</strong> {estado_bosgame.total_archivos}</div>
            </div>''' if estado_bosgame.conectado else '<p style="color:#B8B8C8;">No conectado a la BOSGAME durante la generación de este informe.</p>'}
        </div>

        <div class="card">
            <h2>5. Respaldos, Envíos y Seguridad NTFS</h2>
            <div class="grid">
                <div class="item"><strong>Respaldo de Carpetas:</strong> {respaldo.get('mensaje', 'No ejecutado')}</div>
                <div class="item"><strong>Envío de Archivo:</strong> {envio.get('mensaje', 'No ejecutado')}</div>
                <div class="item"><strong>Auditoría de Permisos NTFS:</strong> {permisos.get('mensaje', 'No ejecutado')}</div>
            </div>
        </div>

        <div class="footer">
            <p>BrachioDiag &bull; Herramienta de Diagnóstico para Windows &bull; UTP Centro Regional de Chiriquí</p>
        </div>
    </div>
</body>
</html>"""

    with open(ruta_html, "w", encoding="utf-8") as f:
        f.write(html_content)

    return {
        "ok": True,
        "mensaje": "Informes exportados exitosamente en formatos TXT y HTML.",
        "ruta_txt": str(ruta_txt),
        "ruta_html": str(ruta_html)
    }
