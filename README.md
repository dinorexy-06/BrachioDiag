# 🦕 BrachioDiag - Suite de Diagnóstico, Respaldo y Administración para Windows

> **Universidad Tecnológica de Panamá (UTP)**  
> **Centro Regional de Chiriquí**  
> **Licenciatura en Desarrollo y Gestión de Software**  
> **Materia:** Sistemas Operativos  
> **Desarrolladora:** Angélica Serracín  

---

## 📋 Descripción General

**BrachioDiag** es una aplicación de escritorio nativa con interfaz gráfica (GUI) desarrollada en Python y Tkinter para Windows. Cuenta con una arquitectura **100% responsive**, adaptativa y fluida, operando **sin privilegios de administrador**, **sin conexión a Internet** y **utilizando únicamente la biblioteca estándar de Python** (cero dependencias externas vía `pip`).

Permite auditar el estado del hardware, monitorear el rendimiento en tiempo real, explorar y administrar el sistema de archivos, inspeccionar el software y eventos del sistema, conectar carpetas compartidas en red local (BOSGAME `192.168.100.10`), crear respaldos comprimidos (.zip), editar y transferir archivos en red, y verificar empíricamente el modelo de seguridad y control de acceso (DACL) de NTFS con `icacls`.

---

## 🌟 Características Técnicas

* **100% Nativo y Portable:** Sin `pip`, sin `psutil`, sin `customtkinter` ni `Pillow`. Funciona de forma inmediata en cualquier equipo con Python 3.8 o superior.
* **Encabezado Adaptable sin Altura Fija:**
  * La altura del encabezado se deriva dinámicamente de su contenido (el logo de 64×64 px y las líneas de texto calculadas con `font.metrics("linespace")`), asegurando que **nunca se corte el logo ni el texto inferior**.
  * **Subtítulo con medición inteligente:** Con `font.measure()`, la app determina si el texto secundario cabe completo:
    * **Modo amplio:** `"Desarrolladora: Angélica Serracín | UTP - Sistemas Operativos"`.
    * **Modo medio:** `"Angélica Serracín · Sistemas Operativos"`.
    * **Modo compacto:** Se oculta automáticamente para priorizar el título y controles.
  * **Indicador BOSGAME dinámico:** Muestra el estado completo en modo amplio, versión resumida en modo medio y punto de color interactivo en modo compacto, con tooltip informativo flotante al pasar el puntero.
* **Menú Lateral con Ancho Dinámico y Nombres Completos:**
  * **Ancho calculado según el contenido:** Se mide el texto más largo mediante `font.measure()` sumando el icono, márgenes y la barra de desplazamiento. Los nombres **nunca se truncan con puntos suspensivos ("…")**.
  * **Ajuste en dos líneas (`wraplength`):** En pantallas pequeñas o con escalados altos de DPI (125%, 150%), los textos largos crecen en altura en dos líneas sin perder legibilidad.
  * **Eliminación del modo "solo iconos":** El menú siempre presenta las opciones con su texto descriptivo completo.
* **Botón Hamburguesa `☰` Interactivo:**
  * Siempre visible en el encabezado con un área táctil cómoda (≥ 40×40 px), cursor de mano y resaltado visual cuando el menú está abierto.
  * **En escritorio (Modos Amplio y Medio):** Al presionar `☰`, el menú lateral se oculta y el área de contenido se expande al 100% del ancho disponible; al presionar de nuevo, reaparece acoplado a la izquierda.
  * **En Modo Compacto (< 900 px):** El menú permanece oculto por defecto para aprovechar el espacio. Al pulsar `☰`, se despliega como un **panel superpuesto (overlay)** sobre el contenido con un telón de fondo oscuro. Se cierra automáticamente al elegir cualquier herramienta, al pulsar `☰`, al hacer clic fuera del panel o con la tecla **`Escape`**.
  * **Atajo de Teclado:** Presiona **`Ctrl + M`** en cualquier momento para mostrar u ocultar el menú.
* **Emblema Oficial Integrado:**
  * `assets/icono.ico`: Ícono oficial de Windows asignado a la ventana y a la barra de tareas mediante `SetCurrentProcessExplicitAppUserModelID`.
  * `assets/logo_pequeno.png`: Emblema transparente de 64×64 px en el encabezado y como favicon en el informe HTML.
  * `assets/logo_grande.png`: Emblema transparente de 420 px centrado en Inicio y en "Acerca de", con el nombre **BrachioDiag** y subtítulo `"Herramienta de diagnóstico para Windows"` renderizados como texto tipográfico en rosado, reduciéndose suavemente con `subsample(2)` en pantallas compactas.
* **Procesamiento Asíncrono (`threading`):** Tareas pesadas (pings continuos, escaneo de archivos pesados, compresión ZIP, transferencias SMB) corren en hilos secundarios manteniendo la interfaz gráfica ágil y sin congelamientos.

---

## 🏗️ Arquitectura del Proyecto

```text
BrachioDiag/
│
├── BrachioDiag.pyw               # Interfaz gráfica principal responsive (Tkinter / Canvas / Threading)
├── estilos.py                    # Constantes de diseño, paleta morado/rosado, fuentes, breakpoints y estilos ttk
├── logica.py                     # Módulo de lógica del sistema operativo y llamadas Win32
├── BrachioDiag.py                # Lanzador puente para consola
├── ejecutar_BrachioDiag.bat      # Lanzador oficial por lotes (doble clic sin consola negra)
├── README.md                     # Documentación técnica general
├── GUIA_SUSTENTACION.md          # Guion de defensa, evidencias y banco de preguntas
│
├── assets/                       # Recursos gráficos oficiales
│   ├── icono.ico                 # Icono multirresolución de Windows (16x16 a 256x256)
│   ├── logo_pequeno.png          # Emblema oficial de cabecera y favicon (64x64 px transparente)
│   └── logo_grande.png           # Emblema oficial de alta definición (420 px transparente)
│
└── BrachioDiag_Workspace/        # Directorio de trabajo seguro generado automáticamente al ejecutar
    ├── prueba_seguridad_ntfs.txt # Archivo para auditoría de permisos icacls
    ├── BrachioDiag_Informe_*.txt # Informe compilado en texto plano
    └── BrachioDiag_Informe_*.html# Informe interactivo responsive con apertura en navegador
```

---

## 📊 Las 10 Herramientas del Menú Lateral

| N.º | Herramienta | Subsistema de Windows | Descripción Funcional |
| :---: | :--- | :--- | :--- |
| **1** | **Inicio e información** | Hardware / Kernel | Emblema oficial, tacómetro de salud (0-100%), CPU, Uptime, RAM Win32, usuario, hostname y barras proporcionales. |
| **2** | **Monitor rendimiento** | Rendimiento en Vivo | Medición en tiempo real de CPU (`GetSystemTimes`) y RAM (`GlobalMemoryStatusEx`) con gráfico dinámico de 60 s en `Canvas` que se adapta al ancho total si se oculta el menú. |
| **3** | **Discos y archivos** | Almacenamiento / FS | Resumen de particiones, explorador de archivos con CRUD seguro y buscador asíncrono de los 20 archivos más pesados con doble scrollbar. |
| **4** | **Programas y errores** | Registro / EventLog | Pestañas responsive: Programas instalados (`HKLM`/`HKCU` Uninstall con buscador), Programas de inicio y Registro de eventos (`wevtutil`). |
| **5** | **Configuración IP** | Red / Sockets | Tabla responsive de adaptadores de red, direcciones IPv4, máscara de subred, puerta de enlace y dirección física MAC (`ipconfig /all`). |
| **6** | **Conexión a BOSGAME** | Red Local / SMB | Formulario adaptable con IP, usuario, contraseña oculta y carpeta compartida. Latencia con gráfico Canvas, sondeo de puerto 445 y montaje SMB. |
| **7** | **Respaldo de carpetas** | Compresión / ZIP | Genera respaldos `.zip` hacia la máquina local o hacia BOSGAME con barra de progreso elástica, exclusión de ciclos y asistente de restauración. |
| **8** | **Editor y envío** | E/S / Transferencia | Editor de archivos `.txt` y panel de envío en 3 columnas adaptativas (o apiladas verticalmente en compacto) hacia BOSGAME con verificación de integridad. |
| **9** | **Permisos de archivos** | Seguridad NTFS | Asignación granular con `icacls` (Lectura, Escritura, Ejecución, Modificar, Eliminar, Control Total), pruebas empíricas de lectura/escritura y restauración original. |
| **10**| **Informe diagnóstico** | Auditoría y Reportes | Exportación dual a `.txt` y `.html` interactivo y responsive con apertura en navegador, integrando los emblemas en base64. |
| **—** | **Acerca de** | Ficha de Autoría | Tarjeta centrada con el emblema grande, información formal de la estudiante: Angélica Serracín, materia, carrera y mensaje de agradecimiento. |
| **—** | **Salir** | Control de Ventana | Cuadro de confirmación antes de cerrar. |

---

## 🚀 Instrucciones de Ejecución

### Opción 1: Lanzador Directo (Recomendado)
Haz doble clic sobre:
```cmd
ejecutar_BrachioDiag.bat
```
*Inicia la aplicación con `pythonw.exe` sin abrir ninguna consola negra de fondo.*

### Opción 2: Doble Clic en el Archivo Python
```cmd
BrachioDiag.pyw
```

### Opción 3: Desde Terminal de Comandos
```powershell
python BrachioDiag.py
```

---

## 💻 Atajos de Teclado y Controles de Interfaz

* **`Ctrl + M`**: Mostrar u ocultar el menú lateral en cualquier resolución.
* **Botón `☰` (Cabecera)**: Mostrar/ocultar menú acoplado en escritorio o abrir/cerrar panel superpuesto en modo compacto.
* **`Escape`**: Cerrar el menú superpuesto en modo compacto o salir del modo pantalla completa.
* **`F11`**: Alternar entre Pantalla Completa y Modo Ventana.
* **Rueda del Ratón**: Desplazamiento fluido en el menú lateral y en el panel de contenido principal.
