# Diccionario de datos de la instalación nueva

Generado desde `backend/ctf/adapters/persistence/models.py`. No describe el esquema histórico.

Los nombres de tabla están entre comillas para conservar MAYÚSCULAS en PostgreSQL.
Los prefijos GRM, LBM, RGP y RCP distinguen uniones y finalizaciones. RCP es la tabla adicional que impide puntuar dos veces el mismo reto por usuario.

`cor_resultado` conserva resuelta/expirada/cancelada cuando cor_estado pasa a reiniciando/liberada; `cor_piloto` excluye pruebas del ranking; `ret_piloto_aprobado` se escribe solo tras verificar y limpiar; `snp_prueba_aprobada` acredita la prueba posterior al snapshot.

## GRUPOS

| Campo | Tipo | Nulo | Valor inicial |
| --- | --- | --- | --- |
| `gru_id` | UUID | No | gen_random_uuid() |
| `gru_codigo` | VARCHAR(30) | No | — |
| `gru_nombre` | VARCHAR(100) | No | — |
| `gru_descripcion` | TEXT | No | '' |
| `gru_creado_en` | TIMESTAMP WITH TIME ZONE | No | now() |

## LABORATORIOS

| Campo | Tipo | Nulo | Valor inicial |
| --- | --- | --- | --- |
| `lab_id` | UUID | No | gen_random_uuid() |
| `lab_codigo` | VARCHAR(30) | No | — |
| `lab_nombre` | VARCHAR(100) | No | — |
| `lab_descripcion` | TEXT | No | '' |
| `lab_segmento` | VARCHAR(40) | No | — |
| `lab_estado` | VARCHAR(15) | No | 'planned' |

## MAQUINAS_VIRTUALES

| Campo | Tipo | Nulo | Valor inicial |
| --- | --- | --- | --- |
| `maq_id` | UUID | No | gen_random_uuid() |
| `maq_nombre` | VARCHAR(60) | No | — |
| `maq_tipo` | VARCHAR(12) | No | — |
| `maq_so` | VARCHAR(60) | No | — |
| `maq_ip` | INET | No | — |
| `maq_vlan` | INTEGER | No | — |
| `maq_estado` | VARCHAR(15) | No | 'planned' |
| `maq_creado_en` | TIMESTAMP WITH TIME ZONE | No | now() |
| `maq_actualizado_en` | TIMESTAMP WITH TIME ZONE | No | now() |

## ROLES

| Campo | Tipo | Nulo | Valor inicial |
| --- | --- | --- | --- |
| `rol_id` | INTEGER | No | — |
| `rol_nombre` | VARCHAR(30) | No | — |

## CONEXIONES_GUACAMOLE

| Campo | Tipo | Nulo | Valor inicial |
| --- | --- | --- | --- |
| `con_id` | UUID | No | gen_random_uuid() |
| `con_maquina_id` | UUID | No | — |
| `con_nombre` | VARCHAR(80) | No | — |
| `con_protocolo` | VARCHAR(10) | No | 'ssh' |
| `con_puerto` | INTEGER | No | 22 |
| `con_guacamole_id_externo` | VARCHAR(80) | Sí | — |
| `con_creado_en` | TIMESTAMP WITH TIME ZONE | No | now() |

## LABORATORIO_MAQUINAS

| Campo | Tipo | Nulo | Valor inicial |
| --- | --- | --- | --- |
| `lbm_id` | UUID | No | gen_random_uuid() |
| `lbm_laboratorio_id` | UUID | No | — |
| `lbm_maquina_id` | UUID | No | — |

## USUARIOS

| Campo | Tipo | Nulo | Valor inicial |
| --- | --- | --- | --- |
| `usu_id` | UUID | No | gen_random_uuid() |
| `usu_username` | VARCHAR(50) | No | — |
| `usu_email` | VARCHAR(120) | Sí | — |
| `usu_password_hash` | VARCHAR(200) | No | — |
| `usu_rol_id` | INTEGER | No | — |
| `usu_nombre_completo` | VARCHAR(120) | Sí | — |
| `usu_debe_cambiar_clave` | BOOLEAN | No | false |
| `usu_version_sesion` | INTEGER | No | 0 |
| `usu_estado` | VARCHAR(15) | No | 'activo' |
| `usu_creado_en` | TIMESTAMP WITH TIME ZONE | No | now() |
| `usu_actualizado_en` | TIMESTAMP WITH TIME ZONE | No | now() |

## AUDITORIA

| Campo | Tipo | Nulo | Valor inicial |
| --- | --- | --- | --- |
| `aud_id` | UUID | No | gen_random_uuid() |
| `aud_usuario_id` | UUID | Sí | — |
| `aud_accion` | VARCHAR(60) | No | — |
| `aud_entidad` | VARCHAR(40) | No | — |
| `aud_entidad_id` | VARCHAR(60) | No | — |
| `aud_detalle` | JSONB | No | — |
| `aud_creado_en` | TIMESTAMP WITH TIME ZONE | No | now() |

## GRUPOS_MIEMBROS

| Campo | Tipo | Nulo | Valor inicial |
| --- | --- | --- | --- |
| `grm_id` | UUID | No | gen_random_uuid() |
| `grm_grupo_id` | UUID | No | — |
| `grm_usuario_id` | UUID | No | — |
| `grm_agregado_en` | TIMESTAMP WITH TIME ZONE | No | now() |

## MANTENIMIENTO_SNAPSHOTS

| Campo | Tipo | Nulo | Valor inicial |
| --- | --- | --- | --- |
| `snp_id` | UUID | No | gen_random_uuid() |
| `snp_maquina_id` | UUID | No | — |
| `snp_motivo` | TEXT | No | — |
| `snp_estado` | VARCHAR(15) | No | 'pendiente' |
| `snp_prueba_aprobada` | BOOLEAN | No | false |
| `snp_solicitado_en` | TIMESTAMP WITH TIME ZONE | No | now() |
| `snp_resuelto_en` | TIMESTAMP WITH TIME ZONE | Sí | — |
| `snp_resuelto_por` | UUID | Sí | — |

## RANKING

| Campo | Tipo | Nulo | Valor inicial |
| --- | --- | --- | --- |
| `ran_usuario_id` | UUID | No | — |
| `ran_puntos_totales` | INTEGER | No | 0 |
| `ran_retos_completados` | INTEGER | No | 0 |
| `ran_actualizado_en` | TIMESTAMP WITH TIME ZONE | No | now() |

## RETOS

| Campo | Tipo | Nulo | Valor inicial |
| --- | --- | --- | --- |
| `ret_id` | UUID | No | gen_random_uuid() |
| `ret_codigo` | VARCHAR(40) | No | — |
| `ret_nombre` | VARCHAR(120) | No | — |
| `ret_categoria` | VARCHAR(40) | No | 'LAB' |
| `ret_dificultad` | VARCHAR(10) | No | — |
| `ret_tecnica_mitre` | VARCHAR(20) | No | — |
| `ret_puntos` | INTEGER | No | — |
| `ret_descripcion` | TEXT | No | '' |
| `ret_instrucciones` | TEXT | No | '' |
| `ret_estrategia` | VARCHAR(40) | No | — |
| `ret_maquina_victima_id` | UUID | No | — |
| `ret_estado` | VARCHAR(12) | No | 'draft' |
| `ret_piloto_aprobado` | BOOLEAN | No | false |
| `ret_duracion_minutos` | INTEGER | Sí | — |
| `ret_recursos` | JSONB | No | '[]'::jsonb |
| `ret_creado_por` | UUID | Sí | — |
| `ret_creado_en` | TIMESTAMP WITH TIME ZONE | No | now() |

## CORRIDAS

| Campo | Tipo | Nulo | Valor inicial |
| --- | --- | --- | --- |
| `cor_id` | VARCHAR(12) | No | — |
| `cor_reto_id` | UUID | No | — |
| `cor_usuario_id` | UUID | No | — |
| `cor_maquina_victima_id` | UUID | No | — |
| `cor_maquina_atacante_id` | UUID | Sí | — |
| `cor_flag_hash` | VARCHAR(64) | No | '' |
| `cor_estado` | VARCHAR(15) | No | 'en_cola' |
| `cor_resultado` | VARCHAR(15) | Sí | — |
| `cor_piloto` | BOOLEAN | No | false |
| `cor_conexion_externa` | VARCHAR(80) | Sí | — |
| `cor_iniciado_en` | TIMESTAMP WITH TIME ZONE | No | now() |
| `cor_expira_en` | TIMESTAMP WITH TIME ZONE | No | — |
| `cor_finalizado_en` | TIMESTAMP WITH TIME ZONE | Sí | — |

## RETOS_COMPLETADOS

| Campo | Tipo | Nulo | Valor inicial |
| --- | --- | --- | --- |
| `rcp_id` | UUID | No | gen_random_uuid() |
| `rcp_usuario_id` | UUID | No | — |
| `rcp_reto_id` | UUID | No | — |
| `rcp_puntos` | INTEGER | No | — |
| `rcp_creado_en` | TIMESTAMP WITH TIME ZONE | No | now() |

## RETOS_GRUPOS

| Campo | Tipo | Nulo | Valor inicial |
| --- | --- | --- | --- |
| `rgp_id` | UUID | No | gen_random_uuid() |
| `rgp_reto_id` | UUID | No | — |
| `rgp_grupo_id` | UUID | No | — |

## RETOS_PISTAS

| Campo | Tipo | Nulo | Valor inicial |
| --- | --- | --- | --- |
| `pis_id` | UUID | No | gen_random_uuid() |
| `pis_reto_id` | UUID | No | — |
| `pis_orden` | INTEGER | No | — |
| `pis_titulo` | VARCHAR(80) | No | 'Pista' |
| `pis_texto` | TEXT | No | — |
| `pis_descuento_puntos` | INTEGER | No | 0 |

## CORRIDAS_INTENTOS

| Campo | Tipo | Nulo | Valor inicial |
| --- | --- | --- | --- |
| `int_id` | UUID | No | gen_random_uuid() |
| `int_corrida_id` | VARCHAR(12) | No | — |
| `int_valor_hash` | VARCHAR(64) | No | — |
| `int_resultado` | BOOLEAN | No | — |
| `int_enviado_en` | TIMESTAMP WITH TIME ZONE | No | now() |

## PISTAS_USADAS

| Campo | Tipo | Nulo | Valor inicial |
| --- | --- | --- | --- |
| `pud_id` | UUID | No | gen_random_uuid() |
| `pud_usuario_id` | UUID | No | — |
| `pud_reto_id` | UUID | No | — |
| `pud_pista_id` | UUID | No | — |
| `pud_descuento` | INTEGER | No | 0 |

