import sys
sys.path.insert(0, '.')
from clasificador_quinta import ClasificadorQuinta
from pathlib import Path

clf = ClasificadorQuinta()
carpeta = Path('c:/Users/jlopezp/Downloads/ARCHIVOS DE PRUEBA')
pdfs = sorted(carpeta.rglob('*.pdf'))

print(f"Total PDFs: {len(pdfs)}\n")
for pdf in pdfs:
    r = clf.analizar_pdf(pdf)
    persona = str(pdf.parent.name)[:38]
    nombre  = pdf.name[:42]
    cat     = r.get('categoria') or '-'
    met     = r.get('metodo') or '-'
    msg     = r.get('mensaje', '')[:60]
    print(f"[{r['status']}] {persona:<38} | {nombre:<42} | cat={cat} | {msg}")
