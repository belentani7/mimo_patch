# Contribuir

## Flujo

1. Abre un issue describiendo el problema o la propuesta.
2. Crea una rama corta: `feat/...`, `fix/...` o `docs/...`.
3. Aplica el protocolo spec-first y añade tests.
4. Ejecuta la verificación local.
5. Abre un PR completando la checklist de `.github/pull_request_template.md`.

## Comandos

- (sin scripts declarados; documenta aquí los comandos reales)

## Reglas

- Conventional commits.
- Sin secretos ni credenciales.
- Un cambio reversible por PR.
- Revisión de `@belentani7` y CI verde.

<!-- repo-forge:contributing:inicio -->
# Contribuir

## Antes de tocar nada

1. Lee `BIBLIA.md` (doctrina del repositorio) y `plataforma/FICHA.md` (alcance permitido).
2. Ejecuta `python scripts/doctor.py` y guarda la salida: es la línea base.
3. Un cambio resuelve **un solo resultado verificable**.

## Cómo enviar

```bash
git checkout -b fix/<asunto-corto>
# ... cambio mínimo ...
python scripts/doctor.py
git commit -m "fix(alcance): <qué se arregla>"
```

Convención de commit: `type(scope): resumen` con tipos `feat|fix|docs|chore|refactor|test|perf`.

## Qué no se acepta

- Cambios que rompan una regla del catálogo sin justificar la excepción.
- Archivos generados a mano que el build regenera.
- Datos personales, credenciales o capturas de clientes.
- Promesas en el README que el código no cumpla.

<!-- repo-forge:contributing -->
<!-- repo-forge:contributing:fin -->
