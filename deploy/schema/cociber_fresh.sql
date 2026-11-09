-- Instalación NUEVA. Ejecutar solo en una base vacía. No es migración.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE "GRUPOS" (
	gru_id UUID DEFAULT gen_random_uuid() NOT NULL, 
	gru_codigo VARCHAR(30) NOT NULL, 
	gru_nombre VARCHAR(100) NOT NULL, 
	gru_descripcion TEXT DEFAULT '' NOT NULL, 
	gru_creado_en TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (gru_id), 
	UNIQUE (gru_codigo)
);

CREATE TABLE "LABORATORIOS" (
	lab_id UUID DEFAULT gen_random_uuid() NOT NULL, 
	lab_codigo VARCHAR(30) NOT NULL, 
	lab_nombre VARCHAR(100) NOT NULL, 
	lab_descripcion TEXT DEFAULT '' NOT NULL, 
	lab_segmento VARCHAR(40) NOT NULL, 
	lab_estado VARCHAR(15) DEFAULT 'planned' NOT NULL, 
	PRIMARY KEY (lab_id), 
	UNIQUE (lab_codigo)
);

CREATE TABLE "MAQUINAS_VIRTUALES" (
	maq_id UUID DEFAULT gen_random_uuid() NOT NULL, 
	maq_nombre VARCHAR(60) NOT NULL, 
	maq_tipo VARCHAR(12) NOT NULL, 
	maq_so VARCHAR(60) NOT NULL, 
	maq_ip INET NOT NULL, 
	maq_vlan INTEGER NOT NULL, 
	maq_estado VARCHAR(15) DEFAULT 'planned' NOT NULL, 
	maq_creado_en TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	maq_actualizado_en TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (maq_id), 
	CHECK (maq_tipo IN ('atacante','victima')), 
	CHECK (maq_estado IN ('planned','ready','en_uso','mantenimiento','dirty')), 
	UNIQUE (maq_nombre), 
	UNIQUE (maq_ip)
);

CREATE INDEX ix_maq_tipo_estado ON "MAQUINAS_VIRTUALES" (maq_tipo, maq_estado);

CREATE TABLE "ROLES" (
	rol_id SERIAL NOT NULL, 
	rol_nombre VARCHAR(30) NOT NULL, 
	PRIMARY KEY (rol_id), 
	UNIQUE (rol_nombre)
);

CREATE TABLE "CONEXIONES_GUACAMOLE" (
	con_id UUID DEFAULT gen_random_uuid() NOT NULL, 
	con_maquina_id UUID NOT NULL, 
	con_nombre VARCHAR(80) NOT NULL, 
	con_protocolo VARCHAR(10) DEFAULT 'ssh' NOT NULL, 
	con_puerto INTEGER DEFAULT 22 NOT NULL, 
	con_guacamole_id_externo VARCHAR(80), 
	con_creado_en TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (con_id), 
	CHECK (con_protocolo IN ('ssh','rdp','vnc')), 
	FOREIGN KEY(con_maquina_id) REFERENCES "MAQUINAS_VIRTUALES" (maq_id)
);

CREATE TABLE "LABORATORIO_MAQUINAS" (
	lbm_id UUID DEFAULT gen_random_uuid() NOT NULL, 
	lbm_laboratorio_id UUID NOT NULL, 
	lbm_maquina_id UUID NOT NULL, 
	PRIMARY KEY (lbm_id), 
	UNIQUE (lbm_laboratorio_id, lbm_maquina_id), 
	FOREIGN KEY(lbm_laboratorio_id) REFERENCES "LABORATORIOS" (lab_id) ON DELETE CASCADE, 
	FOREIGN KEY(lbm_maquina_id) REFERENCES "MAQUINAS_VIRTUALES" (maq_id) ON DELETE CASCADE
);

CREATE TABLE "USUARIOS" (
	usu_id UUID DEFAULT gen_random_uuid() NOT NULL, 
	usu_username VARCHAR(50) NOT NULL, 
	usu_email VARCHAR(120), 
	usu_password_hash VARCHAR(200) NOT NULL, 
	usu_rol_id INTEGER NOT NULL, 
	usu_nombre_completo VARCHAR(120), 
	usu_debe_cambiar_clave BOOLEAN DEFAULT false NOT NULL, 
	usu_version_sesion INTEGER DEFAULT 0 NOT NULL, 
	usu_estado VARCHAR(15) DEFAULT 'activo' NOT NULL, 
	usu_creado_en TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	usu_actualizado_en TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (usu_id), 
	CHECK (usu_estado IN ('activo','inactivo','bloqueado')), 
	UNIQUE (usu_username), 
	UNIQUE (usu_email), 
	FOREIGN KEY(usu_rol_id) REFERENCES "ROLES" (rol_id)
);

CREATE TABLE "AUDITORIA" (
	aud_id UUID DEFAULT gen_random_uuid() NOT NULL, 
	aud_usuario_id UUID, 
	aud_accion VARCHAR(60) NOT NULL, 
	aud_entidad VARCHAR(40) NOT NULL, 
	aud_entidad_id VARCHAR(60) NOT NULL, 
	aud_detalle JSONB NOT NULL, 
	aud_creado_en TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (aud_id), 
	FOREIGN KEY(aud_usuario_id) REFERENCES "USUARIOS" (usu_id)
);

CREATE TABLE "GRUPOS_MIEMBROS" (
	grm_id UUID DEFAULT gen_random_uuid() NOT NULL, 
	grm_grupo_id UUID NOT NULL, 
	grm_usuario_id UUID NOT NULL, 
	grm_agregado_en TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (grm_id), 
	UNIQUE (grm_grupo_id, grm_usuario_id), 
	FOREIGN KEY(grm_grupo_id) REFERENCES "GRUPOS" (gru_id) ON DELETE CASCADE, 
	FOREIGN KEY(grm_usuario_id) REFERENCES "USUARIOS" (usu_id) ON DELETE CASCADE
);

CREATE TABLE "MANTENIMIENTO_SNAPSHOTS" (
	snp_id UUID DEFAULT gen_random_uuid() NOT NULL, 
	snp_maquina_id UUID NOT NULL, 
	snp_motivo TEXT NOT NULL, 
	snp_estado VARCHAR(15) DEFAULT 'pendiente' NOT NULL, 
	snp_prueba_aprobada BOOLEAN DEFAULT false NOT NULL, 
	snp_solicitado_en TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	snp_resuelto_en TIMESTAMP WITH TIME ZONE, 
	snp_resuelto_por UUID, 
	PRIMARY KEY (snp_id), 
	CHECK (snp_estado IN ('pendiente','en_proceso','confirmado')), 
	FOREIGN KEY(snp_maquina_id) REFERENCES "MAQUINAS_VIRTUALES" (maq_id), 
	FOREIGN KEY(snp_resuelto_por) REFERENCES "USUARIOS" (usu_id)
);

CREATE TABLE "RANKING" (
	ran_usuario_id UUID NOT NULL, 
	ran_puntos_totales INTEGER DEFAULT 0 NOT NULL, 
	ran_retos_completados INTEGER DEFAULT 0 NOT NULL, 
	ran_actualizado_en TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (ran_usuario_id), 
	FOREIGN KEY(ran_usuario_id) REFERENCES "USUARIOS" (usu_id)
);

CREATE TABLE "RETOS" (
	ret_id UUID DEFAULT gen_random_uuid() NOT NULL, 
	ret_codigo VARCHAR(40) NOT NULL, 
	ret_nombre VARCHAR(120) NOT NULL, 
	ret_categoria VARCHAR(40) DEFAULT 'LAB' NOT NULL, 
	ret_dificultad VARCHAR(10) NOT NULL, 
	ret_tecnica_mitre VARCHAR(20) NOT NULL, 
	ret_puntos INTEGER NOT NULL, 
	ret_descripcion TEXT DEFAULT '' NOT NULL, 
	ret_instrucciones TEXT DEFAULT '' NOT NULL, 
	ret_estrategia VARCHAR(40) NOT NULL, 
	ret_maquina_victima_id UUID NOT NULL, 
	ret_estado VARCHAR(12) DEFAULT 'draft' NOT NULL, 
	ret_piloto_aprobado BOOLEAN DEFAULT false NOT NULL, 
	ret_duracion_minutos INTEGER, 
	ret_recursos JSONB DEFAULT '[]'::jsonb NOT NULL, 
	ret_creado_por UUID, 
	ret_creado_en TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (ret_id), 
	CHECK (ret_dificultad IN ('basico','medio','avanzado')), 
	CHECK (ret_estado IN ('draft','published','archived')), 
	CHECK (ret_puntos > 0), 
	UNIQUE (ret_codigo), 
	FOREIGN KEY(ret_maquina_victima_id) REFERENCES "MAQUINAS_VIRTUALES" (maq_id), 
	FOREIGN KEY(ret_creado_por) REFERENCES "USUARIOS" (usu_id)
);

CREATE TABLE "CORRIDAS" (
	cor_id VARCHAR(12) NOT NULL, 
	cor_reto_id UUID NOT NULL, 
	cor_usuario_id UUID NOT NULL, 
	cor_maquina_victima_id UUID NOT NULL, 
	cor_maquina_atacante_id UUID, 
	cor_flag_hash VARCHAR(64) DEFAULT '' NOT NULL, 
	cor_estado VARCHAR(15) DEFAULT 'en_cola' NOT NULL, 
	cor_resultado VARCHAR(15), 
	cor_piloto BOOLEAN DEFAULT false NOT NULL, 
	cor_conexion_externa VARCHAR(80), 
	cor_iniciado_en TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	cor_expira_en TIMESTAMP WITH TIME ZONE NOT NULL, 
	cor_finalizado_en TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (cor_id), 
	CHECK (cor_id ~ '^[a-f0-9]{12}$'), 
	CHECK (cor_estado IN ('en_cola','reservada','activa','resuelta','expirada','cancelada','reiniciando','liberada')), 
	FOREIGN KEY(cor_reto_id) REFERENCES "RETOS" (ret_id), 
	FOREIGN KEY(cor_usuario_id) REFERENCES "USUARIOS" (usu_id), 
	FOREIGN KEY(cor_maquina_victima_id) REFERENCES "MAQUINAS_VIRTUALES" (maq_id), 
	FOREIGN KEY(cor_maquina_atacante_id) REFERENCES "MAQUINAS_VIRTUALES" (maq_id)
);

CREATE UNIQUE INDEX uq_cor_atacante_vivo ON "CORRIDAS" (cor_maquina_atacante_id) WHERE cor_estado IN ('reservada','activa','reiniciando') AND cor_maquina_atacante_id IS NOT NULL;

CREATE UNIQUE INDEX uq_cor_reto_vivo ON "CORRIDAS" (cor_reto_id) WHERE cor_estado IN ('reservada','activa','reiniciando');

CREATE UNIQUE INDEX uq_cor_usuario_pendiente ON "CORRIDAS" (cor_usuario_id, cor_reto_id) WHERE cor_estado IN ('en_cola','reservada','activa','reiniciando');

CREATE UNIQUE INDEX uq_cor_victima_viva ON "CORRIDAS" (cor_maquina_victima_id) WHERE cor_estado IN ('reservada','activa','reiniciando');

CREATE TABLE "RETOS_COMPLETADOS" (
	rcp_id UUID DEFAULT gen_random_uuid() NOT NULL, 
	rcp_usuario_id UUID NOT NULL, 
	rcp_reto_id UUID NOT NULL, 
	rcp_puntos INTEGER NOT NULL, 
	rcp_creado_en TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (rcp_id), 
	UNIQUE (rcp_usuario_id, rcp_reto_id), 
	FOREIGN KEY(rcp_usuario_id) REFERENCES "USUARIOS" (usu_id), 
	FOREIGN KEY(rcp_reto_id) REFERENCES "RETOS" (ret_id)
);

CREATE TABLE "RETOS_GRUPOS" (
	rgp_id UUID DEFAULT gen_random_uuid() NOT NULL, 
	rgp_reto_id UUID NOT NULL, 
	rgp_grupo_id UUID NOT NULL, 
	PRIMARY KEY (rgp_id), 
	UNIQUE (rgp_reto_id, rgp_grupo_id), 
	FOREIGN KEY(rgp_reto_id) REFERENCES "RETOS" (ret_id) ON DELETE CASCADE, 
	FOREIGN KEY(rgp_grupo_id) REFERENCES "GRUPOS" (gru_id) ON DELETE CASCADE
);

CREATE TABLE "RETOS_PISTAS" (
	pis_id UUID DEFAULT gen_random_uuid() NOT NULL, 
	pis_reto_id UUID NOT NULL, 
	pis_orden INTEGER NOT NULL, 
	pis_titulo VARCHAR(80) DEFAULT 'Pista' NOT NULL, 
	pis_texto TEXT NOT NULL, 
	pis_descuento_puntos INTEGER DEFAULT 0 NOT NULL, 
	PRIMARY KEY (pis_id), 
	UNIQUE (pis_reto_id, pis_orden), 
	CHECK (pis_orden BETWEEN 1 AND 3), 
	FOREIGN KEY(pis_reto_id) REFERENCES "RETOS" (ret_id) ON DELETE CASCADE
);

CREATE TABLE "CORRIDAS_INTENTOS" (
	int_id UUID DEFAULT gen_random_uuid() NOT NULL, 
	int_corrida_id VARCHAR(12) NOT NULL, 
	int_valor_hash VARCHAR(64) NOT NULL, 
	int_resultado BOOLEAN NOT NULL, 
	int_enviado_en TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (int_id), 
	FOREIGN KEY(int_corrida_id) REFERENCES "CORRIDAS" (cor_id)
);

CREATE TABLE "PISTAS_USADAS" (
	pud_id UUID DEFAULT gen_random_uuid() NOT NULL, 
	pud_usuario_id UUID NOT NULL, 
	pud_reto_id UUID NOT NULL, 
	pud_pista_id UUID NOT NULL, 
	pud_descuento INTEGER DEFAULT 0 NOT NULL, 
	PRIMARY KEY (pud_id), 
	UNIQUE (pud_usuario_id, pud_pista_id), 
	FOREIGN KEY(pud_usuario_id) REFERENCES "USUARIOS" (usu_id), 
	FOREIGN KEY(pud_reto_id) REFERENCES "RETOS" (ret_id), 
	FOREIGN KEY(pud_pista_id) REFERENCES "RETOS_PISTAS" (pis_id)
);

INSERT INTO "ROLES" (rol_id,rol_nombre) VALUES (1,'administrador'),(2,'instructor'),(3,'player'),(4,'invitado');

COMMIT;
