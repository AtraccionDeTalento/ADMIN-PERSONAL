import sys
sys.path.insert(0, '.')
import fitz
from pathlib import Path

archivos = [
    'c:/Users/jlopezp/Downloads/ARCHIVOS DE PRUEBA/8252 - VICENTE VARA VICTOR HUGO/202602101214456727.pdf',
    'c:/Users/jlopezp/Downloads/ARCHIVOS DE PRUEBA/2700 - RODRIGUEZ ESPINOZA MARIBEL LILI/202602101214456727.pdf',
]

for path in archivos:
    p = Path(path)
    doc = fitz.open(str(p))
    texto = doc[0].get_text()
    print(f"\n{'='*70}")
    print(f"ARCHIVO: {p.parent.name} / {p.name}")
    print(f"TEXTO COMPLETO ({len(texto)} chars):")
    print(texto)
    doc.close()
