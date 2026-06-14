# HeptaSieve

**Privacidad primero, seguro para IA. Sincronización continua y local de Heptabase a Markdown estructurado.**

Tú decides exactamente qué tarjetas puede ver un agente de IA. El resto queda fuera de su alcance.

[English](README.md) · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · Español · [Français](README.fr.md) · [Deutsch](README.de.md) · [العربية](README.ar.md) · [עברית](README.he.md) · [Русский](README.ru.md) · [Українська](README.uk.md)

> Herramienta no oficial. Sin afiliación ni respaldo de Heptabase. Solo macOS por ahora.

---

## Por qué existe

Todo comenzó con un objetivo simple: conectar Heptabase a Claude Code para que un agente de IA pudiera leer mis notas.

La ruta oficial es el [CLI](https://github.com/heptameta/heptabase-cli-skills) propio de Heptabase, que se activa en la app en Settings, AI Features, CLI. Es **fail-open**: una vez que lo autorizas, el agente puede leer toda tu base de conocimiento. Las herramientas de terceros como el servidor `heptabase-mcp` funcionan igual. Eso está bien si todo lo que tienes en tu base de conocimiento es seguro de compartir. Pero si tienes tarjetas confidenciales junto a las que quieres que use la IA, que es lo que hace la mayoría, esta ruta no funciona.

La clave: el muro de privacidad tiene que estar en el límite de *lo que la IA puede leer*. Ese límite vive fuera de Heptabase, en cómo alimentas tus notas al agente. El trabajo real de una herramienta como esta es **mantener las tarjetas confidenciales fuera del alcance de la IA y exportar solo el resto a Markdown legible por IA.** Sincronizar las notas es la mitad fácil.

Eso es el sieve (tamiz). Solo pasan las tarjetas que tú permites.

## Qué hace

HeptaSieve lee directamente tu base de datos local de Heptabase y escribe las tarjetas seleccionadas como archivos Markdown en los destinos que elijas. Un job de `launchd` lo ejecuta cada 15 minutos, manteniendo el Markdown sincronizado con tus notas. El agente de IA solo lee la carpeta de Markdown exportada. Nunca toca la base de datos.

- **Lee la base de datos local en vivo.** Heptabase dejó de ofrecer [copias de seguridad locales automáticas](https://support.heptabase.com/en/articles/11064116-how-does-auto-backup-work-in-heptabase) a finales de 2025, por lo que leer la DB en vivo es ahora la ruta confiable para la sincronización continua local.
- **Conversión fiel a la estructura.** Tablas, listas bullet / todo / toggle, secciones anidadas y videos se obtienen por ingeniería inversa del schema ProseMirror de Heptabase y se renderizan como Markdown limpio.
- **Enrutamiento a cualquier destino.** Cada whiteboard puede ir a su propia carpeta, incluyendo una ruta absoluta que coloca un board directamente en un proyecto separado.

## El modelo de privacidad fail-closed

Una tarjeta se exporta solo si coincide con una de dos listas de permisos explícitas. Por defecto no se lee nada.

| Fuente | Regla |
|---|---|
| **`whitelist_whiteboards`** | Whiteboards que nombras. Solo se leen las tarjetas en la *superficie* de cada board. Los sub-whiteboards no se siguen. Para incluir uno, nómbralo también. |
| **`card_map`** | Una capa `título -> ruta exacta`. Estos títulos siempre se sincronizan y su ruta tiene prioridad. |
| **`blacklist_whiteboards`** | Las tarjetas en estos boards se restan *antes* de que se lea cualquier contenido. La blacklist supera a la whitelist, por lo que una tarjeta colocada en dos boards por error sigue siendo bloqueada. |
| **Sub-whiteboards (sin nombrar)** | Mover una tarjeta a un sub-whiteboard cambia su `whiteboard_id`, por lo que un escaneo de superficie nunca la ve. Excluida por estructura, no por una regla que tengas que recordar. |

La garantía en una línea: cada consulta que toca el título o contenido de una tarjeta está restringida a whiteboard ids en whitelist o títulos de `card_map`. El título y contenido de una tarjeta que no está en whitelist nunca se leen en memoria.

De aquí se derivan dos principios de diseño. **La exclusión estructural supera a la exclusión sustractiva**: una tarjeta a la que la consulta no puede llegar es más segura que una que filtras después de leer. **La mejor notificación es la que nunca necesitas**: la herramienta está diseñada para que nunca tengas que preguntarte si una tarjeta se filtró.

## Cómo se compara

| | HeptaSieve | CLI oficial de Heptabase | Otras herramientas de exportación |
|---|---|---|---|
| Modelo de privacidad | Lista de permisos fail-closed | Fail-open (base de conocimiento completa) | Exportación total |
| Sincronización local continua | Sí (`launchd`, 15 min) | Lectura bajo demanda | Exportación única |
| Lee DB local en vivo | Sí | Varía | Suele necesitar archivo de backup |
| Markdown fiel a la estructura | Tablas, listas, secciones, video | Varía | Varía |
| Enrutamiento por destino por board | Sí, incl. rutas absolutas | No | No |

Esto no es un reemplazo completo de Heptabase, y "mejor que lo oficial" solo se sostiene en tres ejes: privacidad controlable, sincronización local continua y fidelidad de estructura. El público objetivo es intencionalmente reducido: usuarios de macOS que viven en Heptabase y se preocupan por lo que la IA puede ver. Si ese eres tú, esto está construido exactamente para tu caso.

## Instalación

Requisitos: macOS, Python 3.9+, la app desktop de Heptabase instalada.

```bash
git clone https://github.com/yyu0310/heptasieve.git
cd heptasieve
cp config.example.json config.json
```

Luego edita `config.json` (cada campo tiene un comentario inline que lo explica):

1. Confirma que `db_path` apunte a tu `hepta.db` local.
2. Establece `base_output_dir` y `board_output_dir` donde quieras que se escriba el Markdown.
3. Lista los whiteboards que quieres exportar en `whitelist_whiteboards`.
4. Añade cualquier sustitución de ruta precisa en `card_map`.

Ejecuta primero una vista previa, que no escribe nada:

```bash
python3 heptabase_sync.py --dry
```

Cuando el plan parezca correcto, ejecútalo de verdad:

```bash
python3 heptabase_sync.py
```

### Sincronización automática cada 15 minutos

```bash
cp com.example.heptasieve.plist ~/Library/LaunchAgents/
# edita el archivo copiado: establece las rutas absolutas y confirma tu ruta de python3
launchctl load ~/Library/LaunchAgents/com.example.heptasieve.plist
```

## Usarlo con un agente de IA

HeptaSieve incluye documentación legible por agentes para que puedas configurarlo hablando con un agente de codificación IA en lugar de seguir pasos manualmente:

- [`AGENTS.md`](AGENTS.md) y [`CLAUDE.md`](CLAUDE.md): cómo un agente debe razonar y configurar esta herramienta.
- [`llms.txt`](llms.txt): un índice de la documentación para LLMs.
- [`skills/setup-heptasieve/`](skills/setup-heptasieve/): un skill de Claude Code que guía toda la configuración en una sola solicitud.

Apunta tu agente a la carpeta de Markdown exportada, nunca a `hepta.db`. Esa separación es el punto central.

## Cómo funciona

Ver [`ARCHITECTURE.md`](ARCHITECTURE.md) para la arquitectura: el flujo de datos, el ordenamiento fail-closed dentro de `build_plan`, las tablas de base de datos que lee y las invariantes de privacidad que hay que preservar al modificar el código.

## Limitaciones y advertencias honestas

- **El schema es frágil.** Depende de la estructura interna de la base de datos de Heptabase. Una actualización de Heptabase puede romperlo. Es no oficial por naturaleza.
- **Leer la DB en vivo no tiene aprobación oficial.** Funciona bien en la práctica y es de solo lectura, pero debes saber que no es una integración soportada.
- **Solo macOS.** Las rutas y la configuración de `launchd` asumen macOS hoy.

## Licencia

[MIT](LICENSE).
