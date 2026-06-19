import sys
sys.path.insert(0, '.')
import fitz
from pathlib import Path

archivos = [
    'c:/Users/jlopezp/Downloads/ARCHIVOS DE PRUEBA/12486 - CHACON MEDINA ROXANA NORA/DECLARACION JURADA 5TA ROXANA CHACON.pdf',
    'c:/Users/jlopezp/Downloads/ARCHIVOS DE PRUEBA/13187 - GONZALEZ RODRIGUEZ JOSE MANUEL/202602101214456727 (1).pdf',
    'c:/Users/jlopezp/Downloads/ARCHIVOS DE PRUEBA/2030 - CARBAJO JURADO ARMANDO MIGUEL/firma_armando_carbajo.pdf',
    'c:/Users/jlopezp/Downloads/ARCHIVOS DE PRUEBA/20602 - GUILLEN TARAZONA NANCY MARITZA/Documento.pdf',
    'c:/Users/jlopezp/Downloads/ARCHIVOS DE PRUEBA/21242 - QUEVEDO FERRARI CRISALIDA LEONOR/Declaracion Jurada Crisalida Quevedo Ferrari_0001.pdf',
    'c:/Users/jlopezp/Downloads/ARCHIVOS DE PRUEBA/2204 - DONAYRE PACHECO PABLO ALBERTO/declaracion_jurada_firmado.pdf',
    'c:/Users/jlopezp/Downloads/ARCHIVOS DE PRUEBA/2700 - RODRIGUEZ ESPINOZA MARIBEL LILI/202602101214456727.pdf',
    'c:/Users/jlopezp/Downloads/ARCHIVOS DE PRUEBA/3072 - OBREGON TORRES DULA BEATRIZ/ARCHIVO-RENTA DE QUINTA CATEGORIA-2026.pdf',
    'c:/Users/jlopezp/Downloads/ARCHIVOS DE PRUEBA/8252 - VICENTE VARA VICTOR HUGO/202602101214456727.pdf',
]

for path in archivos:
    p = Path(path)
    if not p.exists():
        # intentar buscar coincidencia parcial
        parent = p.parent
        if parent.exists():
            pdfs = list(parent.glob('*.pdf'))
            if pdfs:
                p = pdfs[0]
            else:
                print(f"\n[NO ENCONTRADO] {path}\n"); continue
        else:
            print(f"\n[NO EXISTE CARPETA] {path}\n"); continue
    try:
        doc = fitz.open(str(p))
        texto = doc[0].get_text()
        chars = len(texto.replace(' ','').replace('\n',''))
        print(f"\n{'='*70}")
        print(f"ARCHIVO: {p.name}")
        print(f"Chars extraibles: {chars}")
        print(f"TEXTO (primeros 400 chars):")
        print(texto[:400])
        doc.close()
    except Exception as e:
        print(f"\n[ERROR] {p.name}: {e}")
