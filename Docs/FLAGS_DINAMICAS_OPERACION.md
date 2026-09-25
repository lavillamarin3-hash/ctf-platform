# Operación de flags dinámicas

## Qué se cambió

La plataforma ahora separa el ciclo de flag dinámica en:

1. `FlagService`: generación y expansión de plantilla.
2. `DynamicFlagRuntime`: preparación y limpieza de evidencia.
3. `SSHFlagInjector`: transporte SSH + script remoto de privilegio mínimo.
4. `lab_lock`: aislamiento de la VM compartida mediante Redis.
5. `runs.py`: orquestación HTTP del `ChallengeRun`.

## Qué NO se cambió

- No se añadieron tablas.
- No se añadieron columnas.
- No se ejecutaron migraciones.
- No se ejecutó SQL contra la base de datos del usuario.
- No se realizó ninguna escritura en `192.168.146.137` durante el desarrollo de este paquete.

La persistencia normal de un `ChallengeRun`, `ChallengeRunFlag`, `Submission` o cierre de sesión sigue siendo responsabilidad normal de la aplicación cuando el usuario la ejecuta.

## Modelo actual de aislamiento

La VM `192.168.146.137` es una única instancia física/lógica compartida. Redis la trata como recurso exclusivo mientras exista un `ChallengeRun` activo.

Por eso:

```text
1 estudiante -> 1 ejecución -> 1 VM -> 1 flag dinámica
```

No se permiten dos ejecuciones simultáneas sobre la misma VM.

## Evolución posterior

Cuando exista Nutanix/Prism, el contrato debe evolucionar a:

```text
ChallengeRun
   -> ChallengeInstance
      -> VMAsset
         -> snapshot/baseline
```

y añadir una política de:

```text
reserve -> restore -> inject -> run -> clear -> restore -> release
```

La API actual no depende de esa implementación concreta.
