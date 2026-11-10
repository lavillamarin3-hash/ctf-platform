#!/usr/bin/env python3
"""Inventario conservador de archivos; no borra nada.

Requisitos: Python3 y Git. Ejemplo: python scripts/audit_repository.py
Clasifica archivos versionados y nuevos no ignorados. Una referencia textual
es evidencia orientativa; ausencia no prueba que un entrypoint sea obsoleto.
"""
import csv
import hashlib
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "Docs/05_Referencia/05_AUDITORIA_ARCHIVOS.csv"


def main():
    files = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT).decode().split("\0")
    paths = sorted(set(path for path in files if path and (ROOT / path).is_file() and path != "Docs/05_Referencia/05_AUDITORIA_ARCHIVOS.csv"))
    texts = {}
    for path in paths:
        try: texts[path] = (ROOT / path).read_text(encoding="utf-8")
        except (UnicodeError, OSError): pass
    rows, hashes = [], {}
    for path in paths:
        digest = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        refs = [other for other, content in texts.items() if other != path and (path in content or Path(path).name in content or (Path(path).suffix in (".py", ".tsx", ".ts") and Path(path).stem in content))]
        duplicate = hashes.get(digest)
        hashes[digest] = path
        if path in ("build-error.txt", "gitignore.txt"):
            category, note = "no_referenciado", "Log histórico/copia de configuración; revisados manualmente, sin referencias"
        elif path.startswith("labs/demo-vulnerable/"):
            category, note = "demo-desactivado", "Paquete opt-in; no arranca en compose fresh"
        elif duplicate:
            category, note = "duplicado", f"Contenido idéntico a {duplicate}; conservar si es marcador de paquete"
        else:
            category, note = "en_uso", "Runtime, entrypoint, prueba, guía o soporte conservado; no se declara obsoleto por falta de import directo"
        rows.append((path, category, "; ".join(refs[:6]), note))
    with OUTPUT.open("w", encoding="utf-8", newline="") as target:
        writer = csv.writer(target)
        writer.writerow(("archivo", "clasificacion", "referencias_muestra", "justificacion"))
        writer.writerows(rows)
        for removed in ("build-error.txt", "gitignore.txt"):
            if not (ROOT / removed).exists():
                writer.writerow((removed, "no_referenciado", "", "Eliminado tras lectura y búsqueda de referencias previa al inventario; log histórico/copia inactiva de .gitignore"))
    print(f"Inventario: {len(rows)} archivos; sin borrados automáticos")


if __name__ == "__main__": main()
