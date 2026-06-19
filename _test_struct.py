import sys
sys.path.insert(0, '.')
import fitz
from pathlib import Path

archivos = [
    ('8252 - VICENTE VARA VICTOR HUGO', 'c:/Users/jlopezp/Downloads/ARCHIVOS DE PRUEBA/8252 - VICENTE VARA VICTOR HUGO/202602101214456727.pdf'),
    ('2700 - RODRIGUEZ',                'c:/Users/jlopezp/Downloads/ARCHIVOS DE PRUEBA/2700 - RODRIGUEZ ESPINOZA MARIBEL LILI/202602101214456727.pdf'),
]

for nombre, path in archivos:
    doc = fitz.open(path)
    page = doc[0]
    print(f"\n{'='*65}")
    print(f"PERSONA: {nombre}")

    # --- Texto con posicion ---
    td = page.get_text('dict')
    print("\n-- BLOQUES CON COORDENADAS (solo lineas relevantes) --")
    for block in td.get('blocks', []):
        if block.get('type') != 0: continue
        for line in block.get('lines', []):
            text = ''.join(s.get('text','') for s in line.get('spans',[])).strip()
            if not text: continue
            y = line['bbox'][1]
            x = line['bbox'][0]
            if text.strip() in ('X','x','✓','✗') or '1.-' in text or '2.-' in text or '3.-' in text or 'percibido' in text.lower() or 'No he' in text or 'Si he' in text or 'Sí he' in text:
                print(f"  y={y:6.1f}  x={x:6.1f}  text={repr(text[:70])}")

    # --- Drawings ---
    drawings = page.get_drawings()
    rects = [d for d in drawings if d.get('items') and d['items'][0][0]=='re']
    print(f"\n-- RECTANGULOS (checkboxes potenciales): {len(rects)} total --")
    for d in rects:
        r = d['rect']
        w,h = r.width, r.height
        if 4 < w < 25 and 4 < h < 25:
            print(f"  y={r.y0:6.1f}  x={r.x0:6.1f}  size={w:.1f}x{h:.1f}  color_fill={d.get('fill')}")

    doc.close()
