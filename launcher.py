#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════════════
#  launcher.py  —  Sistema DJ Quinta Categoría (Alternativa a INICIAR.vbs)
#  People Analytics USIL
#
#  Uso: Ejecuta este script cuando INICIAR.vbs no funcione
#    • Diagnóstico automático
#    • Inicia servidor Flask
#    • Abre navegador
#    • Log de errores
# ═══════════════════════════════════════════════════════════════════════════════

import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass
import os
import subprocess
import time
import socket
import webbrowser
from pathlib import Path

# Colores para terminal
class Color:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def log(msg, level="INFO"):
    """Imprime mensaje con timestamp."""
    timestamp = time.strftime("%H:%M:%S")
    if level == "INFO":
        print(f"[{timestamp}] ℹ️  {msg}")
    elif level == "OK":
        print(f"{Color.OKGREEN}[{timestamp}] ✓ {msg}{Color.ENDC}")
    elif level == "ERROR":
        print(f"{Color.FAIL}[{timestamp}] ✗ {msg}{Color.ENDC}")
    elif level == "WARN":
        print(f"{Color.WARNING}[{timestamp}] ⚠ {msg}{Color.ENDC}")

def diagnostico():
    """Verifica que todo esté listo."""
    print(f"\n{Color.BOLD}═══ DIAGNOSTICO INICIAL ═══{Color.ENDC}\n")
    
    BASE_DIR = Path(__file__).parent
    VENV_PYTHON = BASE_DIR / "venv" / "Scripts" / "python.exe"
    VENV_PYTHONW = BASE_DIR / "venv" / "Scripts" / "pythonw.exe"
    SERVIDOR = BASE_DIR / "servidor_dj_quinta.py"
    
    # 1. Verificar venv
    if not VENV_PYTHON.exists():
        log("❌ Entorno virtual NO ENCONTRADO", "ERROR")
        log(f"   Ruta esperada: {VENV_PYTHON}", "INFO")
        log("   Solución: Ejecuta INSTALAR.bat primero", "WARN")
        return False
    log(f"✓ Entorno virtual encontrado", "OK")
    
    # 2. Verificar servidor
    if not SERVIDOR.exists():
        log("❌ servidor_dj_quinta.py NO ENCONTRADO", "ERROR")
        log(f"   Ruta esperada: {SERVIDOR}", "INFO")
        return False
    log(f"✓ servidor_dj_quinta.py encontrado", "OK")
    
    # 3. Probar venv
    try:
        result = subprocess.run(
            [str(VENV_PYTHON), "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            log(f"✓ Python funcional: {result.stdout.strip()}", "OK")
        else:
            log(f"❌ Python NO funciona: {result.stderr}", "ERROR")
            return False
    except Exception as e:
        log(f"❌ Error testando Python: {e}", "ERROR")
        return False
    
    # 4. Verificar puerto 5010
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    puerto_libre = sock.connect_ex(('127.0.0.1', 5010)) != 0
    sock.close()
    
    if not puerto_libre:
        log("⚠ Puerto 5010 ya está en uso (¿servidor previo?)", "WARN")
        log("  Intentando liberar puerto...", "INFO")
        try:
            subprocess.run(
                'taskkill /F /FI "WINDOWTITLE eq Sistema*" 2>nul',
                shell=True,
                timeout=3
            )
            time.sleep(1)
        except:
            pass
    else:
        log("✓ Puerto 5010 disponible", "OK")
    
    print()
    return True


def iniciar_servidor():
    """Inicia el servidor Flask."""
    BASE_DIR = Path(__file__).parent
    VENV_PYTHONW = BASE_DIR / "venv" / "Scripts" / "pythonw.exe"
    SERVIDOR = BASE_DIR / "servidor_dj_quinta.py"
    
    print(f"\n{Color.BOLD}═══ INICIANDO SERVIDOR ═══{Color.ENDC}\n")
    
    try:
        log("Iniciando servidor en http://localhost:5010", "INFO")
        
        # Usar pythonw.exe para que no muestre ventana
        # Si no existe, usar python.exe
        py_exe = VENV_PYTHONW if VENV_PYTHONW.exists() else (BASE_DIR / "venv" / "Scripts" / "python.exe")
        
        proceso = subprocess.Popen(
            [str(py_exe), str(SERVIDOR)],
            cwd=str(BASE_DIR),
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        log(f"✓ Servidor iniciado (PID: {proceso.pid})", "OK")
        
        # Esperar a que esté listo
        log("Esperando que servidor esté listo...", "INFO")
        for i in range(30):  # 30 intentos = ~30 segundos
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                resultado = sock.connect_ex(('127.0.0.1', 5010))
                sock.close()
                
                if resultado == 0:
                    log("✓ Servidor listo para recibir conexiones", "OK")
                    return True
            except:
                pass
            
            time.sleep(1)
            if (i + 1) % 5 == 0:
                log(f"  Esperando... ({i + 1}s)", "INFO")
        
        log("⚠ Servidor posiblemente listo (timeout en verificación)", "WARN")
        return True
        
    except Exception as e:
        log(f"❌ Error iniciando servidor: {e}", "ERROR")
        return False


def abrir_navegador():
    """Abre el navegador en la URL."""
    print(f"\n{Color.BOLD}═══ ABRIENDO NAVEGADOR ═══{Color.ENDC}\n")
    
    try:
        url = "http://localhost:5010"
        log(f"Abriendo {url}", "INFO")
        webbrowser.open(url)
        log("✓ Navegador abierto", "OK")
    except Exception as e:
        log(f"⚠ No se pudo abrir navegador: {e}", "WARN")
        log(f"  Ingresa manualmente a: http://localhost:5010", "INFO")


def main():
    """Función principal."""
    print(f"\n{Color.BOLD}{Color.HEADER}")
    print("╔═══════════════════════════════════════════════════════╗")
    print("║  Sistema DJ Quinta Categoría  ·  People Analytics    ║")
    print("║  Launcher · Puerto 5010                               ║")
    print("╚═══════════════════════════════════════════════════════╝")
    print(f"{Color.ENDC}\n")
    
    # Diagnóstico
    if not diagnostico():
        log("\n❌ El diagnóstico encontró problemas. No se puede iniciar.", "ERROR")
        print("\nPresiona ENTER para cerrar...")
        input()
        sys.exit(1)
    
    # Iniciar
    if not iniciar_servidor():
        log("\n❌ No se pudo iniciar el servidor.", "ERROR")
        print("\nPresiona ENTER para cerrar...")
        input()
        sys.exit(1)
    
    # Abrir navegador
    time.sleep(2)
    abrir_navegador()
    
    print(f"\n{Color.BOLD}{Color.OKGREEN}")
    print("╔═══════════════════════════════════════════════════════╗")
    print("║  ✓ Sistema iniciado correctamente                    ║")
    print("║  El navegador se abrirá automáticamente.             ║")
    print("║  Si no abre, ve a: http://localhost:5010             ║")
    print("╚═══════════════════════════════════════════════════════╝")
    print(f"{Color.ENDC}\n")
    
    log("Presiona ENTER para cerrar este launcher (servidor continúa ejecutándose)...", "INFO")
    input()


if __name__ == "__main__":
    main()
