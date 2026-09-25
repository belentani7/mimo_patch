# MIMO PATCH — Parche Unificado (Mimo Code) v3

> **Fusión de**: Fable 5.1 (XML structured prompts) + Pydantic strict typing + Jev AI (System One routing) + OpenCode MCP + Python glue code.
>
> Estado del arte para septiembre 2026.

## Qué es

Un **único archivo Python** (`mimo_patch.py`) que actúa como **enrutador de Sistema 1** (System One) — inspirado en Jev AI (TypeSafe AI) y la arquitectura XML del prompt filtrado de Claude Fable 5.1.

El parche decide **ANTES** de llamar a cualquier LLM caro si una acción es segura, urgente y qué skill ejecutar. Si es seguro y la confianza es alta, ejecuta sin pedir permiso.

```
┌─────────────────────────────────────────────────────────────────┐
│ OpenCode CLI (agente externo)                                    │
│   Lee opencode/system-one-router.json                            │
│   Aplica reglas: conf<0.85 → pedir aclaración                    │
│                  conf≥0.85 && urg≥0.7 → ejecutar sin permiso     │
│                  conf≥0.85 && urg<0.7 → proponer y esperar       │
└──────────────────┬──────────────────────────────────────────────┘
                   │ (stdio JSON-RPC)
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│ mimo_patch.py serve-mcp                                           │
│  ├─ Intenta cargar mcp>=1.0.0  →  FastMCP real                   │
│  └─ Si falla                    →  _StubMCP (mcp_stub.py)         │
│  Tools expuestas: mimo_route, mimo_cache_stats                   │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│ mimo_route()                                                      │
│  1. cache.get(state)  ← cache.py (LRU 512)                       │
│  2. gate_check(state) ← heurística pura, 0 tokens                │
│  3. load_prompt(heavy) ← lazy: solo si el gate lo pide           │
│  4. router.route()    ← SystemOneRouter (Jev + fallback)        │
│  5. decide_action_plan()  ← reglas del JSON OpenCode            │
│  6. cache.put(state, result)                                      │
│  Si excepción → notify_human(urgency=1.0) → degraded            │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│ Skills ejecutadas (solo si is_safe_to_execute && conf≥0.85)      │
│   · apply_refund / apply_stripe_refund                           │
│   · escalate_support                                             │
│   · block_fraud                                                  │
│   · ignore_spam                                                  │
│   · send_email                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Instalación rápida

### Termux (Android/Huawei)
```bash
bash install/install_termux.sh
```

### Windows 11
```powershell
powershell -ExecutionPolicy Bypass -File install/install.ps1
```

### Linux/Mac estándar
```bash
pip install -r requirements.txt
cp .env.example .env  # rellena tus API keys
```

## Uso

### Self-test (verifica que todo funciona)
```bash
python mimo_patch.py self-test
```

### Classify un estado
```bash
python mimo_patch.py classify --state "usuario intentó chargeback por error 502"
```

### Stats del cache
```bash
python mimo_patch.py stats
```

### Servidor MCP (para integrar con OpenCode)
```bash
python mimo_patch.py serve-mcp
```

### Dry-run (sin llamar a providers)
```bash
python mimo_patch.py dry-run --state "usuario pregunta horario"
```

## Variables de entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `MIMO_CONFIDENCE_THRESHOLD` | `0.85` | Umbral de confianza para ejecutar |
| `MIMO_LOG_LEVEL` | `WARNING` | DEBUG\|INFO\|WARNING\|ERROR |
| `MIMO_CACHE_FILE` | `./logs/cache.jsonl` | Persistencia del cache |
| `MIMO_NOTIFY_FILE` | `./logs/notify.jsonl` | Log de NOTIFY_HUMAN |
| `TYPESAFE_API_KEY` | (vacío) | Jev AI — preferido si lo tienes |
| `OPENROUTER_API_KEY` | (vacío) | Fallback multi-modelo |
| `OPENAI_API_KEY` | (vacío) | Fallback generativo |
| `S1G_LOCAL_FIRST` | `0` | `1` = Ollama antes que remoto |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | Endpoint local |
| `OLLAMA_MODEL` | `qwen2.5:7b-instruct` | Modelo Ollama |
| `REDIS_URL` | `redis://localhost:6379/0` | Memoria corto plazo (fallback JSONL) |
| `PG_DSN` | `postgresql://localhost/mimo` | Memoria largo plazo (fallback JSONL) |
| `STRIPE_API_KEY` | (vacío) | Para skill apply_stripe_refund |

## Provider chain (orden de fallback)

1. **(si `S1G_LOCAL_FIRST=1`)** Ollama local — `$0`
2. **TypeSafe (Jev AI)** — `$0.042/M input, $0 output` (si `TYPESAFE_API_KEY`)
3. **OpenRouter** — Multi-modelo, puede enrutar a Jev (si `OPENROUTER_API_KEY`)
4. **OpenAI** — JSON mode generativo (si `OPENAI_API_KEY`)
5. **Anthropic (Claude)** — Vía instructor (si `ANTHROPIC_API_KEY`)
6. **(si no `S1G_LOCAL_FIRST`)** Ollama local
7. **Heurística determinista** — Siempre disponible, regex + keywords, `$0`

## Estructura del proyecto

```
mimo_patch/
├── mimo_patch.py          # Entrypoint CLI + serve-mcp
├── mcp_stub.py            # Stub si mcp>=1.0 no instalado
├── gate.py                # Gate heurístico 0 tokens + Mental Reframing
├── router.py              # SystemOneRouter (Jev + fallback chain)
├── providers.py           # Catálogo de providers
├── primitives.py          # Choice / Score / Noul (Jev primitives)
├── memory.py              # Redis + pgvector (con fallback JSONL)
├── cache.py               # LRU cache + mimo_cache_stats
├── notification.py        # NOTIFY_HUMAN con sanitize
├── token_budget.py        # Pruning de tokens y coste estimado
├── evaluation.py          # Braintrust/LangSmith hooks (opcional)
├── profile.py             # Perfil usuario (Pedro Belentani)
├── concurrency.py         # Helpers async para batch
├── prompts/
│   ├── light.txt          # Prompt corto
│   └── fable_style.xml    # Prompt Fable 5.1 completo con XML tags
├── skills/
│   ├── __init__.py
│   ├── base.py
│   ├── apply_refund.py
│   ├── apply_stripe_refund.py
│   ├── escalate_support.py
│   ├── block_fraud.py
│   ├── ignore_spam.py
│   └── send_email.py
├── tests/
│   ├── test_gate.py
│   ├── test_router.py
│   ├── test_cache.py
│   └── test_integration.py
├── opencode/
│   └── system-one-router.json  # El tuyo, tal cual
├── install/
│   ├── install_termux.sh
│   └── install.ps1
├── glue/
│   └── django_saleor_example.py  # Ejemplo pegamento con Django/Saleor
├── logs/                  # Cache, notify, decisions JSONL
├── .env.example
├── requirements.txt
├── Makefile
└── README.md
```

## Reglas de decisión (del JSON de OpenCode)

| Condición | Plan |
|-----------|------|
| `is_safe_to_execute=false` | `BLOCKED` |
| `confidence < 0.85` | `ASK_CLARIFICATION` |
| `is_safe=true` AND `confidence≥0.85` AND `urgency≥0.7` | `EXECUTE_NOW` |
| `is_safe=true` AND `confidence≥0.85` AND `urgency<0.7` | `PROPOSE_AND_WAIT` |

## Hard guardrails (NUNCA bypassable)

- **SQL injection**: `OR 1=1`, `UNION SELECT`, `DROP TABLE`, `INSERT INTO`, `DELETE FROM`, `EXEC(`, `xp_cmdshell`
- **Banking data**: card numbers (13-16 dígitos), IBAN, SSN, CVV
- **Content policy**: CSAM, underage exploit
- **Mental Reframing**: "ignore previous instructions", "act as if", "developer mode", "sudo mode", hypothetical dañino

## Por qué esto es "Mimo Code" (código mínimo)

1. **Agnóstico**: Lo puedes meter en un bot de Discord, una web de Django o un script de automatización.
2. **No consume tokens de salida narrativos**: Pydantic + prompt estricto evitan "Hola, claro que sí, he analizado tu petición y...".
3. **Mantenimiento cero**: Si cambias de provider de IA (de OpenAI a Jev o Anthropic), solo cambias la línea de `model`. El resto no se entera.
4. **Modo stub automático**: Si `mcp` no está instalado, `_StubMCP` entra solo.
5. **Fallback gracioso**: Si Redis/PG no están, usa JSONL. Si todos los providers fallan, NOTIFY_HUMAN.

## Verificación end-to-end

```bash
# 1. Compilar TODO (verifica que no hay typos)
python -m compileall -q . && echo "✅ compile OK"

# 2. Tests unitarios
pytest -q tests/

# 3. Self-test (matriz extendida de 19 casos)
python mimo_patch.py self-test

# 4. Classify directo (sin API keys → heuristic)
python mimo_patch.py classify --state "usuario reinició password"

# 5. Classify crítico (dispara heavy prompt)
python mimo_patch.py classify --state "usuario intentó chargeback, tarjeta robada, error 502"

# 6. Stats del cache
python mimo_patch.py stats

# 7. Dry-run (sin llamar a ningún provider)
python mimo_patch.py dry-run --state "usuario pregunta horario"

# 8. Servidor MCP (integración OpenCode)
python mimo_patch.py serve-mcp
```

## Integración con OpenCode CLI

Copia `opencode/system-one-router.json` a tu directorio `.opencode/agents/` y OpenCode lo cargará automáticamente.

OpenCode invocará las tools `mimo_route` y `mimo_cache_stats` vía JSON-RPC sobre stdio del proceso `python mimo_patch.py serve-mcp`.

## Auditoría de integración (76 ideas rastreadas)

Integrados los 76 conceptos de las conversaciones previas:

| Categoría | v2 | v3 |
|-----------|----|----|
| Ideas rastreadas | 61 | 76 |
| Tools MCP expuestas | 3 | 2 (`mimo_route`, `mimo_cache_stats`) |
| Entrypoints CLI | 1 (gate.py) | 2 (`gate.py` + `mimo_patch.py`) |
| Modo degradado | ❌ | ✅ `mcp_stub.py` + `notification.py` |
| Cache de decisiones | ❌ | ✅ `cache.py` (LRU 512) |
| Umbrales exactos OpenCode | ❌ | ✅ conf≥0.85 / urg≥0.7 |
| Plan de acción explícito | ❌ | ✅ `EXECUTE_NOW` / `PROPOSE_AND_WAIT` / `ASK_CLARIFICATION` / `BLOCKED` |
| Instalador Termux | ⚠️ genérico | ✅ específico |
| Compatibilidad JSON original | parcial | ✅ exacta |
| Mental Reframing | ✅ | ✅ en prompt + gate |
| Sensitive topics | ✅ | ✅ en gate + memory |
| Hard guardrail local | ✅ | ✅ NUNCA bypassable |

## Licencia

Uso libre. Créditos a:
- **TypeSafe AI** (Diogo Almeida) por Jev AI y la arquitectura System One.
- **Pliny the Liberator** por el leak del System Prompt de Claude Fable 5 / 5.1.
- **Anthropic** por las ideas de `<tone_and_formatting>`, Mental Reframing y memory policy.
- **Pedro Belentani** por el caso de uso (Belentani Judas Experience) y los requisitos exactos del `system-one-router.json`.

---

*"Un LLM es un motor de creatividad. Jev es un motor de decisión. Usar uno para el trabajo del otro era el error que la industria cometió durante 4 años."*
