"""Exporta DDL y diccionario desde los modelos usados por la instalación nueva.

Desde backend: python -m ctf.infrastructure.export_schema
No conecta a ninguna base ni imprime secretos.
"""
from pathlib import Path
from sqlalchemy.schema import CreateIndex, CreateTable
from sqlalchemy.dialects.postgresql import dialect
from ..adapters.persistence.models import Base


def export():
    root = Path(__file__).resolve().parents[3]
    sql_path = root / "deploy/schema/cociber_fresh.sql"
    dictionary = root / "Docs/DICCIONARIO_FRESH.md"
    sql_path.parent.mkdir(parents=True, exist_ok=True)
    statements = ["-- Instalación NUEVA. Ejecutar solo en una base vacía. No es migración.", "BEGIN;", "CREATE EXTENSION IF NOT EXISTS pgcrypto;"]
    doc = ["# Diccionario de datos de la instalación nueva", "", "Generado desde `backend/ctf/adapters/persistence/models.py`. No describe el esquema histórico.", "",
           "Los nombres de tabla están entre comillas para conservar MAYÚSCULAS en PostgreSQL.", "Los prefijos GRM, LBM, RGP y RCP distinguen uniones y finalizaciones. RCP es la tabla adicional que impide puntuar dos veces el mismo reto por usuario.", "",
           "`cor_resultado` conserva resuelta/expirada/cancelada cuando cor_estado pasa a reiniciando/liberada; `cor_piloto` excluye pruebas del ranking; `ret_piloto_aprobado` se escribe solo tras verificar y limpiar; `snp_prueba_aprobada` acredita la prueba posterior al snapshot.", ""]
    for table in Base.metadata.sorted_tables:
        statements.append(str(CreateTable(table).compile(dialect=dialect())).strip() + ";")
        for index in sorted(table.indexes, key=lambda i: i.name): statements.append(str(CreateIndex(index).compile(dialect=dialect())) + ";")
        doc.extend([f"## {table.name}", "", "| Campo | Tipo | Nulo | Valor inicial |", "| --- | --- | --- | --- |"])
        for column in table.columns:
            default = str(column.server_default.arg) if column.server_default is not None else "—"
            doc.append(f"| `{column.name}` | {column.type.compile(dialect=dialect())} | {'Sí' if column.nullable else 'No'} | {default} |")
        doc.append("")
    statements.extend(["INSERT INTO \"ROLES\" (rol_id,rol_nombre) VALUES (1,'administrador'),(2,'instructor'),(3,'player'),(4,'invitado');", "COMMIT;"])
    sql_path.write_text("\n\n".join(statements) + "\n", encoding="utf-8")
    dictionary.write_text("\n".join(doc) + "\n", encoding="utf-8")


if __name__ == "__main__": export()
