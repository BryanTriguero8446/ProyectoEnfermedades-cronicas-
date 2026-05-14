SET FOREIGN_KEY_CHECKS = 0;
SET sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ENGINE_SUBSTITUTION';

DROP DATABASE IF EXISTS clinical_db;
CREATE DATABASE clinical_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE clinical_lens_db;

-- =============================================================
-- TABLA: rol
-- =============================================================
CREATE TABLE rol (
  id          TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
  nombre      VARCHAR(30)      NOT NULL,
  descripcion VARCHAR(120)     NULL,
  activo      TINYINT(1)       NOT NULL DEFAULT 1,
  PRIMARY KEY (id),
  UNIQUE KEY uq_rol_nombre (nombre)
) ENGINE=InnoDB;

INSERT INTO rol (nombre, descripcion) VALUES
  ('administrador', 'Gestiona usuarios y supervisa el sistema'),
  ('paciente',      'Ingresa datos clínicos y consulta predicciones');

-- =============================================================
-- TABLA: usuario
-- =============================================================
CREATE TABLE usuario (
  id                 BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT,
  nombre             VARCHAR(80)      NOT NULL,
  apellido           VARCHAR(80)      NOT NULL,
  correo             VARCHAR(180)     NOT NULL,
  contrasena_hash    VARCHAR(255)     NOT NULL COMMENT 'bcrypt/argon2 hash — nunca texto plano',
  id_rol             TINYINT UNSIGNED NOT NULL DEFAULT 2,
  activo             TINYINT(1)       NOT NULL DEFAULT 1,
  bloqueado          TINYINT(1)       NOT NULL DEFAULT 0,
  intentos_fallidos  TINYINT UNSIGNED NOT NULL DEFAULT 0,
  ultimo_acceso      DATETIME         NULL,
  fecha_registro     DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
  fecha_actualizacion DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_usuario_correo (correo),
  KEY idx_usuario_rol (id_rol),
  KEY idx_usuario_activo (activo),
  CONSTRAINT fk_usuario_rol FOREIGN KEY (id_rol) REFERENCES rol (id)
    ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

-- =============================================================
-- TABLA: historial_accesos
-- =============================================================
CREATE TABLE historial_accesos (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  id_usuario  BIGINT UNSIGNED NOT NULL,
  accion      ENUM('login_ok','login_fail','logout','cambio_pass','bloqueo') NOT NULL,
  ip          VARCHAR(45)     NULL COMMENT 'IPv4 o IPv6',
  user_agent  VARCHAR(255)    NULL,
  fecha_hora  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_historial_usuario (id_usuario),
  KEY idx_historial_fecha   (fecha_hora),
  CONSTRAINT fk_historial_usuario FOREIGN KEY (id_usuario) REFERENCES usuario (id)
    ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

-- =============================================================
-- TABLA: paciente
-- =============================================================
CREATE TABLE paciente (
  id               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  id_usuario       BIGINT UNSIGNED NOT NULL,
  fecha_nacimiento DATE            NOT NULL,
  genero           ENUM('masculino','femenino','otro') NOT NULL,
  telefono         VARCHAR(20)     NULL,
  direccion        VARCHAR(200)    NULL,
  fecha_registro   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_paciente_usuario (id_usuario),
  CONSTRAINT fk_paciente_usuario FOREIGN KEY (id_usuario) REFERENCES usuario (id)
    ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

-- =============================================================
-- TABLA: datos_clinicos
-- =============================================================
CREATE TABLE datos_clinicos (
  id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  id_paciente         BIGINT UNSIGNED NOT NULL,
  edad                TINYINT UNSIGNED NOT NULL        COMMENT 'años',
  peso                DECIMAL(5,2)    NOT NULL         COMMENT 'kg',
  altura              DECIMAL(4,2)    NOT NULL         COMMENT 'metros',
  imc                 DECIMAL(5,2)    NOT NULL         COMMENT 'calculado automáticamente',
  presion_sistolica   SMALLINT UNSIGNED NOT NULL       COMMENT 'mmHg',
  presion_diastolica  SMALLINT UNSIGNED NOT NULL       COMMENT 'mmHg',
  glucosa             DECIMAL(6,2)    NOT NULL         COMMENT 'mg/dL',
  colesterol          DECIMAL(6,2)    NULL             COMMENT 'mg/dL',
  frecuencia_cardiaca SMALLINT UNSIGNED NOT NULL       COMMENT 'bpm',
  actividad_fisica    ENUM('sedentario','leve','moderado','intenso') NOT NULL DEFAULT 'sedentario',
  fuma                TINYINT(1)      NOT NULL DEFAULT 0,
  alcohol             TINYINT(1)      NOT NULL DEFAULT 0,
  observaciones       TEXT            NULL,
  fecha_registro      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  fecha_actualizacion DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_datos_paciente (id_paciente),
  KEY idx_datos_fecha    (fecha_registro),
  CONSTRAINT fk_datos_paciente FOREIGN KEY (id_paciente) REFERENCES paciente (id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  -- Restricciones de dominio médico
  CONSTRAINT chk_edad           CHECK (edad BETWEEN 1 AND 120),
  CONSTRAINT chk_peso           CHECK (peso BETWEEN 1.00 AND 500.00),
  CONSTRAINT chk_altura         CHECK (altura BETWEEN 0.50 AND 2.50),
  CONSTRAINT chk_presion_s      CHECK (presion_sistolica BETWEEN 60 AND 250),
  CONSTRAINT chk_presion_d      CHECK (presion_diastolica BETWEEN 40 AND 180),
  CONSTRAINT chk_glucosa        CHECK (glucosa BETWEEN 20.00 AND 800.00),
  CONSTRAINT chk_colesterol     CHECK (colesterol IS NULL OR colesterol BETWEEN 50.00 AND 700.00),
  CONSTRAINT chk_frec_cardiaca  CHECK (frecuencia_cardiaca BETWEEN 30 AND 250),
  CONSTRAINT chk_presion_orden  CHECK (presion_sistolica > presion_diastolica)
) ENGINE=InnoDB;

-- =============================================================
-- TABLA: prediccion
-- =============================================================
CREATE TABLE prediccion (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  id_datos        BIGINT UNSIGNED NOT NULL,
  nivel_riesgo    ENUM('bajo','medio','alto') NOT NULL,
  probabilidad    DECIMAL(5,4)    NOT NULL   COMMENT '0.0000 a 1.0000',
  modelo_version  VARCHAR(20)     NOT NULL DEFAULT '1.0',
  factores_json   JSON            NULL       COMMENT 'feature importances del modelo',
  recomendaciones TEXT            NULL,
  fecha           DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_prediccion_datos (id_datos)    COMMENT 'un registro clínico → una predicción',
  KEY idx_pred_riesgo (nivel_riesgo),
  KEY idx_pred_fecha  (fecha),
  CONSTRAINT fk_pred_datos FOREIGN KEY (id_datos) REFERENCES datos_clinicos (id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT chk_probabilidad CHECK (probabilidad BETWEEN 0.0000 AND 1.0000)
) ENGINE=InnoDB;

-- =============================================================
-- TABLA: alerta
-- =============================================================
CREATE TABLE alerta (
  id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  id_datos     BIGINT UNSIGNED NOT NULL,
  tipo         ENUM('glucosa_alta','glucosa_baja','presion_alta','imc_alto',
                    'imc_bajo','frecuencia_anormal','riesgo_alto') NOT NULL,
  nivel        ENUM('advertencia','critico') NOT NULL DEFAULT 'advertencia',
  mensaje      VARCHAR(300)    NOT NULL,
  leida        TINYINT(1)      NOT NULL DEFAULT 0,
  fecha        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_alerta_datos  (id_datos),
  KEY idx_alerta_leida  (leida),
  CONSTRAINT fk_alerta_datos FOREIGN KEY (id_datos) REFERENCES datos_clinicos (id)
    ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

-- =============================================================
-- TABLA: reporte
-- =============================================================
CREATE TABLE reporte (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  id_paciente     BIGINT UNSIGNED NOT NULL,
  tipo            ENUM('clinico','prediccion','evolucion','general') NOT NULL,
  formato         ENUM('pdf','csv') NOT NULL DEFAULT 'pdf',
  ruta_archivo    VARCHAR(300)    NULL        COMMENT 'path relativo en servidor',
  generado_por    BIGINT UNSIGNED NULL        COMMENT 'id del usuario que generó',
  fecha_generacion DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_reporte_paciente (id_paciente),
  KEY idx_reporte_fecha    (fecha_generacion),
  CONSTRAINT fk_reporte_paciente FOREIGN KEY (id_paciente) REFERENCES paciente (id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_reporte_generador FOREIGN KEY (generado_por) REFERENCES usuario (id)
    ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB;

-- =============================================================
-- TABLA: historial_clinico  (resumen narrativo del paciente)
-- =============================================================
CREATE TABLE historial_clinico (
  id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  id_paciente  BIGINT UNSIGNED NOT NULL,
  descripcion  TEXT            NOT NULL,
  tipo         ENUM('ingreso','evolucion','alta','nota') NOT NULL DEFAULT 'nota',
  creado_por   BIGINT UNSIGNED NULL,
  fecha        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_histclin_paciente (id_paciente),
  CONSTRAINT fk_histclin_paciente FOREIGN KEY (id_paciente) REFERENCES paciente (id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_histclin_creador FOREIGN KEY (creado_por) REFERENCES usuario (id)
    ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB;

-- =============================================================
-- TABLA: audit_log  (pista de auditoría genérica)
-- =============================================================
CREATE TABLE audit_log (
  id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  id_usuario   BIGINT UNSIGNED NULL,
  tabla        VARCHAR(60)     NOT NULL,
  operacion    ENUM('INSERT','UPDATE','DELETE') NOT NULL,
  registro_id  BIGINT UNSIGNED NULL,
  datos_antes  JSON            NULL,
  datos_despues JSON           NULL,
  fecha        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_audit_tabla   (tabla),
  KEY idx_audit_usuario (id_usuario),
  KEY idx_audit_fecha   (fecha)
) ENGINE=InnoDB;

-- =============================================================
-- TRIGGERS
-- =============================================================

DELIMITER $$

-- TRIGGER 1: Calcular IMC automáticamente al insertar datos_clinicos
CREATE TRIGGER trg_calcular_imc_insert
BEFORE INSERT ON datos_clinicos
FOR EACH ROW
BEGIN
  IF NEW.altura <= 0 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'La altura debe ser mayor a 0';
  END IF;
  SET NEW.imc = ROUND(NEW.peso / (NEW.altura * NEW.altura), 2);
END$$

-- TRIGGER 2: Recalcular IMC al actualizar peso o altura
CREATE TRIGGER trg_calcular_imc_update
BEFORE UPDATE ON datos_clinicos
FOR EACH ROW
BEGIN
  IF NEW.altura <= 0 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'La altura debe ser mayor a 0';
  END IF;
  SET NEW.imc = ROUND(NEW.peso / (NEW.altura * NEW.altura), 2);
END$$

-- TRIGGER 3: Generar alertas automáticamente al insertar datos_clinicos
CREATE TRIGGER trg_generar_alertas_insert
AFTER INSERT ON datos_clinicos
FOR EACH ROW
BEGIN
  -- Glucosa alta (diabetes)
  IF NEW.glucosa > 125 THEN
    INSERT INTO alerta (id_datos, tipo, nivel, mensaje)
    VALUES (NEW.id, 'glucosa_alta', 
            IF(NEW.glucosa > 200, 'critico', 'advertencia'),
            CONCAT('Glucosa en ayunas elevada: ', NEW.glucosa, ' mg/dL. Valor normal < 100 mg/dL.'));
  END IF;

  -- Glucosa baja (hipoglucemia)
  IF NEW.glucosa < 70 THEN
    INSERT INTO alerta (id_datos, tipo, nivel, mensaje)
    VALUES (NEW.id, 'glucosa_baja', 'critico',
            CONCAT('Hipoglucemia detectada: ', NEW.glucosa, ' mg/dL. Consulte un médico.'));
  END IF;

  -- Presión arterial alta
  IF NEW.presion_sistolica >= 140 OR NEW.presion_diastolica >= 90 THEN
    INSERT INTO alerta (id_datos, tipo, nivel, mensaje)
    VALUES (NEW.id, 'presion_alta',
            IF(NEW.presion_sistolica >= 180 OR NEW.presion_diastolica >= 120, 'critico', 'advertencia'),
            CONCAT('Presión arterial elevada: ', NEW.presion_sistolica, '/', NEW.presion_diastolica, 
                   ' mmHg. Normal: <120/80 mmHg.'));
  END IF;

  -- IMC alto (obesidad)
  IF NEW.imc >= 30 THEN
    INSERT INTO alerta (id_datos, tipo, nivel, mensaje)
    VALUES (NEW.id, 'imc_alto',
            IF(NEW.imc >= 40, 'critico', 'advertencia'),
            CONCAT('IMC elevado: ', NEW.imc, '. Clasificación: ',
              CASE
                WHEN NEW.imc >= 40 THEN 'Obesidad mórbida'
                WHEN NEW.imc >= 35 THEN 'Obesidad grado II'
                ELSE 'Obesidad grado I'
              END));
  END IF;

  -- IMC bajo (desnutrición)
  IF NEW.imc < 18.5 THEN
    INSERT INTO alerta (id_datos, tipo, nivel, mensaje)
    VALUES (NEW.id, 'imc_bajo', 'advertencia',
            CONCAT('IMC bajo: ', NEW.imc, '. Posible desnutrición o bajo peso.'));
  END IF;

  -- Frecuencia cardíaca anormal
  IF NEW.frecuencia_cardiaca < 50 OR NEW.frecuencia_cardiaca > 120 THEN
    INSERT INTO alerta (id_datos, tipo, nivel, mensaje)
    VALUES (NEW.id, 'frecuencia_anormal',
            IF(NEW.frecuencia_cardiaca < 40 OR NEW.frecuencia_cardiaca > 150, 'critico', 'advertencia'),
            CONCAT('Frecuencia cardíaca fuera de rango: ', NEW.frecuencia_cardiaca, ' bpm. Normal: 60-100 bpm.'));
  END IF;
END$$

-- TRIGGER 4: Alerta cuando la predicción es riesgo alto
CREATE TRIGGER trg_alerta_prediccion_alta
AFTER INSERT ON prediccion
FOR EACH ROW
BEGIN
  IF NEW.nivel_riesgo = 'alto' THEN
    INSERT INTO alerta (id_datos, tipo, nivel, mensaje)
    VALUES (NEW.id_datos, 'riesgo_alto', 'critico',
            CONCAT('El modelo predictivo detectó RIESGO ALTO de enfermedad crónica con ',
                   ROUND(NEW.probabilidad * 100, 1), '% de probabilidad. Consulte a un médico.'));
  END IF;
END$$

-- TRIGGER 5: Bloquear usuario tras 5 intentos fallidos
CREATE TRIGGER trg_bloqueo_intentos
AFTER INSERT ON historial_accesos
FOR EACH ROW
BEGIN
  DECLARE v_intentos INT;
  IF NEW.accion = 'login_fail' THEN
    UPDATE usuario
      SET intentos_fallidos = intentos_fallidos + 1
    WHERE id = NEW.id_usuario;

    SELECT intentos_fallidos INTO v_intentos
    FROM usuario WHERE id = NEW.id_usuario;

    IF v_intentos >= 5 THEN
      UPDATE usuario SET bloqueado = 1 WHERE id = NEW.id_usuario;
      INSERT INTO historial_accesos (id_usuario, accion, ip)
      VALUES (NEW.id_usuario, 'bloqueo', NEW.ip);
    END IF;
  END IF;

  -- Resetear intentos en login exitoso
  IF NEW.accion = 'login_ok' THEN
    UPDATE usuario
      SET intentos_fallidos = 0, ultimo_acceso = NOW()
    WHERE id = NEW.id_usuario;
  END IF;
END$$

-- TRIGGER 6: Auditoría — registrar cambios en datos_clinicos
CREATE TRIGGER trg_audit_datos_clinicos_update
AFTER UPDATE ON datos_clinicos
FOR EACH ROW
BEGIN
  INSERT INTO audit_log (tabla, operacion, registro_id, datos_antes, datos_despues)
  VALUES (
    'datos_clinicos', 'UPDATE', NEW.id,
    JSON_OBJECT('peso', OLD.peso, 'glucosa', OLD.glucosa,
                'presion_sistolica', OLD.presion_sistolica,
                'presion_diastolica', OLD.presion_diastolica),
    JSON_OBJECT('peso', NEW.peso, 'glucosa', NEW.glucosa,
                'presion_sistolica', NEW.presion_sistolica,
                'presion_diastolica', NEW.presion_diastolica)
  );
END$$

-- TRIGGER 7: Auditoría — registrar eliminación de datos_clinicos
CREATE TRIGGER trg_audit_datos_clinicos_delete
BEFORE DELETE ON datos_clinicos
FOR EACH ROW
BEGIN
  INSERT INTO audit_log (tabla, operacion, registro_id, datos_antes)
  VALUES (
    'datos_clinicos', 'DELETE', OLD.id,
    JSON_OBJECT('id_paciente', OLD.id_paciente, 'glucosa', OLD.glucosa,
                'imc', OLD.imc, 'fecha_registro', OLD.fecha_registro)
  );
END$$

DELIMITER ;

-- =============================================================
-- PROCEDIMIENTOS ALMACENADOS
-- =============================================================

DELIMITER $$

-- Procedimiento: obtener resumen clínico de un paciente
CREATE PROCEDURE sp_resumen_paciente(IN p_id_paciente BIGINT UNSIGNED)
BEGIN
  SELECT
    u.nombre, u.apellido, u.correo,
    p.fecha_nacimiento,
    TIMESTAMPDIFF(YEAR, p.fecha_nacimiento, CURDATE()) AS edad_actual,
    p.genero,
    COUNT(dc.id)                  AS total_registros,
    MAX(dc.fecha_registro)        AS ultimo_registro,
    AVG(dc.glucosa)               AS promedio_glucosa,
    AVG(dc.imc)                   AS promedio_imc,
    AVG(dc.presion_sistolica)     AS promedio_presion_s,
    AVG(dc.presion_diastolica)    AS promedio_presion_d,
    SUM(CASE WHEN pr.nivel_riesgo = 'alto'  THEN 1 ELSE 0 END) AS predicciones_alto,
    SUM(CASE WHEN pr.nivel_riesgo = 'medio' THEN 1 ELSE 0 END) AS predicciones_medio,
    SUM(CASE WHEN pr.nivel_riesgo = 'bajo'  THEN 1 ELSE 0 END) AS predicciones_bajo,
    SUM(CASE WHEN a.leida = 0 THEN 1 ELSE 0 END)               AS alertas_pendientes
  FROM paciente p
  JOIN usuario u ON p.id_usuario = u.id
  LEFT JOIN datos_clinicos dc ON dc.id_paciente = p.id
  LEFT JOIN prediccion pr ON pr.id_datos = dc.id
  LEFT JOIN alerta a ON a.id_datos = dc.id
  WHERE p.id = p_id_paciente
  GROUP BY u.nombre, u.apellido, u.correo, p.fecha_nacimiento, p.genero;
END$$

-- Procedimiento: últimos N registros clínicos de un paciente
CREATE PROCEDURE sp_historial_clinico(
  IN p_id_paciente BIGINT UNSIGNED,
  IN p_limite      INT
)
BEGIN
  SELECT
    dc.*,
    pr.nivel_riesgo,
    ROUND(pr.probabilidad * 100, 1) AS probabilidad_pct,
    pr.recomendaciones
  FROM datos_clinicos dc
  LEFT JOIN prediccion pr ON pr.id_datos = dc.id
  WHERE dc.id_paciente = p_id_paciente
  ORDER BY dc.fecha_registro DESC
  LIMIT p_limite;
END$$

DELIMITER ;

-- =============================================================
-- VISTAS ÚTILES
-- =============================================================

-- Vista: dashboard administrador (resumen de pacientes con riesgo alto)
CREATE VIEW vw_riesgo_alto AS
SELECT
  p.id                            AS id_paciente,
  u.nombre, u.apellido, u.correo,
  dc.glucosa, dc.imc,
  dc.presion_sistolica, dc.presion_diastolica,
  pr.nivel_riesgo,
  ROUND(pr.probabilidad * 100, 1) AS probabilidad_pct,
  pr.recomendaciones,
  pr.fecha                        AS fecha_prediccion
FROM prediccion pr
JOIN datos_clinicos dc ON pr.id_datos = dc.id
JOIN paciente p  ON dc.id_paciente = p.id
JOIN usuario u   ON p.id_usuario   = u.id
WHERE pr.nivel_riesgo = 'alto'
ORDER BY pr.probabilidad DESC;

-- Vista: alertas pendientes con datos del paciente
CREATE VIEW vw_alertas_pendientes AS
SELECT
  a.id            AS id_alerta,
  a.tipo, a.nivel, a.mensaje, a.fecha,
  p.id            AS id_paciente,
  u.nombre, u.apellido, u.correo
FROM alerta a
JOIN datos_clinicos dc ON a.id_datos = dc.id
JOIN paciente p        ON dc.id_paciente = p.id
JOIN usuario u         ON p.id_usuario   = u.id
WHERE a.leida = 0
ORDER BY a.nivel DESC, a.fecha DESC;

-- Vista: evolución de indicadores por paciente
CREATE VIEW vw_evolucion_indicadores AS
SELECT
  dc.id_paciente,
  u.nombre, u.apellido,
  dc.fecha_registro,
  dc.peso, dc.imc, dc.glucosa,
  dc.presion_sistolica, dc.presion_diastolica,
  dc.frecuencia_cardiaca,
  pr.nivel_riesgo,
  ROUND(pr.probabilidad * 100, 1) AS probabilidad_pct
FROM datos_clinicos dc
JOIN paciente p  ON dc.id_paciente = p.id
JOIN usuario u   ON p.id_usuario   = u.id
LEFT JOIN prediccion pr ON pr.id_datos = dc.id
ORDER BY dc.id_paciente, dc.fecha_registro;

-- =============================================================
-- ÍNDICES ADICIONALES DE RENDIMIENTO
-- =============================================================
CREATE INDEX idx_datos_glucosa     ON datos_clinicos (glucosa);
CREATE INDEX idx_datos_imc         ON datos_clinicos (imc);
CREATE INDEX idx_datos_presion     ON datos_clinicos (presion_sistolica, presion_diastolica);
CREATE INDEX idx_pred_nivel_fecha  ON prediccion (nivel_riesgo, fecha);
CREATE INDEX idx_alerta_tipo       ON alerta (tipo, nivel);

-- =============================================================
-- DATOS SEMILLA (seed data)
-- =============================================================
INSERT INTO usuario (nombre, apellido, correo, contrasena_hash, id_rol) VALUES
  ('Admin', 'Sistema', 'admin@clinicallens.bo',
   '$2b$12$placeholder_hash_admin', 1);

SET FOREIGN_KEY_CHECKS = 1;

-- =============================================================
-- VERIFICACIÓN FINAL
-- =============================================================
SELECT
  TABLE_NAME        AS `Tabla`,
  TABLE_ROWS        AS `Filas estimadas`,
  ENGINE,
  TABLE_COLLATION
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'clinical_lens_db'
ORDER BY TABLE_NAME;
