# PROJECT_MASTER_PROMPT — MIMO PATCH — router seguro de agentes y decisión previa a LLM

**Canon de producto y prompt de ejecución · 2026-10-22 · repositorio belentani7/mimo_patch**

## Identidad y código observado

Python con mimo_patch.py, gate.py, router.py, cache.py, evaluation.py, MCP e integración OpenCode en opencode/. El README describe clasificación previa a LLM, umbrales de confianza, caché, Mimo MCP, acciones posibles como reembolsar o enviar correo; la regla actual menciona ejecutar automáticamente sobre confidence>=0.85 y urgencia elevada. Esas condiciones **no bastan para autorizar acciones sensibles**.

## Máximo potencial — visión norte

Consolidar un router de agente ultrarrápido, tipado y verificable que reduzca coste de tokens, enrute habilidades y proteja procesos contra errores, prompt-injection y acciones no autorizadas; la autonomía se limita estrictamente por alcance del permiso, no por autoconfianza del modelo.

## Experiencia de producto futura

CLI y MCP con `classify`, `dry-run`, `stats`, self-test; rutas explicables, política visible, trazas locales con secretos redactados, caché con expiración y invalidación, fallback sin proveedores y simulador de resultados. Las operaciones de riesgo requieren plan visible, confirmación explícita o delegación previamente autorizada con límites finos.

## Arquitectura y estructuras de evolución

Separar clasificación heurística, score no calibrado, evaluación de política, autorización y ejecutor. El umbral estadístico no sustituye permisos: herramientas de pago, email, bloqueos de cuentas y reembolsos deben usar políticas explícitas, control de scopes, presupuestos, idempotencia y logs mínimos. Validar payloads con esquemas estrictos y tratar resultados externos como datos no confiables. Tests de inyección, escalada, fallos y latencias.

## Entregas priorizadas

1) `python mimo_patch.py self-test` y tests existentes. 2) Revisar gate y impedir que score autorice operaciones sensibles por sí mismo. 3) Formalizar modelo Allow/Deny/Confirm + simulador y trazabilidad. 4) Testear MCP real/stub, caché y degradación de proveedores. 5) Benchmarks reproducibles con métricas reales de precisión, coste y falsos positivos.

## Límites

Nunca ejecutar transferencias, reembolsos, envío de mensajes, bloqueos de cuenta, eliminación de datos o cambios de seguridad únicamente por confianza o urgencia.

## Instrucción maestra para agentes de construcción
**Antes de actuar:** leer este documento y luego contrastarlo con el código, README, configuración, tests y estado real; etiquetar funciones como implementadas, parciales o propuestas. Preservar identidad, arquitectura y datos. No inventar un segundo repositorio, no eliminar historia ni modificar visibilidad o desplegar sin validación. Implementar un incremento funcional de extremo a extremo, no una auditoría sin cambios. Probar caso feliz, errores, seguridad, accesibilidad y costes. No presentar placeholders como producto ni resultados sintéticos como evidencia. **Prompt activador:** «Eres el equipo senior completo de producto, diseño, ingeniería y QA de ESTE repositorio. Materializa el máximo potencial definido aquí, respetando el estado comprobado y trabajando en el código real. Escoge la siguiente mejora de mayor valor, implementa, prueba y deja evidencia reproducible y límites explícitos».
