# HeptaSieve

**Vie privée d'abord, sûr pour l'IA. Synchronisation locale et continue de Heptabase vers Markdown structuré.**

Vous décidez exactement quelles cartes un agent IA peut voir. Le reste reste hors de portée.

[English](README.md) · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [Español](README.es.md) · Français · [Deutsch](README.de.md) · [العربية](README.ar.md) · [עברית](README.he.md) · [Русский](README.ru.md) · [Українська](README.uk.md)

> Outil non officiel. Sans affiliation ni approbation de Heptabase. macOS uniquement pour l'instant.

---

## Pourquoi ça existe

Tout a commencé par un objectif simple : connecter Heptabase à Claude Code pour qu'un agent IA puisse lire mes notes.

La voie officielle est le [CLI](https://github.com/heptameta/heptabase-cli-skills) de Heptabase lui-même, que vous activez dans l'app sous Settings, AI Features, CLI. C'est **fail-open** : une fois autorisé, l'agent peut lire toute votre base de connaissances. Les outils tiers comme le serveur `heptabase-mcp` fonctionnent de la même façon. C'est bien si tout ce que vous avez dans votre base de connaissances peut être partagé. Mais si vous gardez des cartes confidentielles à côté de celles que vous voulez utiliser avec une IA, ce que fait la plupart des gens, cette voie ne fonctionne pas.

L'idée centrale : le mur de confidentialité doit se trouver à la frontière de *ce que l'IA peut lire*. Cette frontière vit en dehors de Heptabase, dans la façon dont vous transmettez vos notes à l'agent. Le vrai travail d'un outil comme celui-ci est donc **de garder les cartes confidentielles hors de portée de l'IA et d'exporter uniquement le reste en Markdown lisible par l'IA.** Synchroniser les notes est la moitié facile.

C'est le sieve (tamis). Seules les cartes que vous autorisez passent.

## Ce qu'il fait

HeptaSieve lit directement votre base de données Heptabase locale et écrit les cartes sélectionnées en fichiers Markdown aux destinations que vous choisissez. Une tâche `launchd` l'exécute toutes les 15 minutes pour que le Markdown reste synchronisé avec vos notes. L'agent IA ne lit que le dossier Markdown exporté. Il ne touche jamais à la base de données.

- **Lit la base de données locale en direct.** Heptabase a cessé de proposer des [sauvegardes locales automatiques](https://support.heptabase.com/en/articles/11064116-how-does-auto-backup-work-in-heptabase) fin 2025, donc lire la DB en direct est maintenant la voie fiable pour la synchronisation continue locale.
- **Conversion fidèle à la structure.** Les tableaux, les listes bullet / todo / toggle, les sections imbriquées et les vidéos sont obtenus par ingénierie inverse du schéma ProseMirror de Heptabase et rendus en Markdown propre.
- **Routage vers n'importe quelle destination.** Chaque whiteboard peut aller dans son propre dossier, y compris un chemin absolu qui place un board directement dans un projet séparé.

## Le modèle de confidentialité fail-closed

Une carte n'est exportée que si elle correspond à l'une des deux listes d'autorisation explicites. Rien n'est lu par défaut.

| Source | Règle |
|---|---|
| **`whitelist_whiteboards`** | Les whiteboards que vous nommez. Seules les cartes sur la *surface* de chaque board sont lues. Les sous-whiteboards ne sont pas suivis. Pour en inclure un, nommez-le aussi. |
| **`card_map`** | Une couche `titre -> chemin exact`. Ces titres sont toujours synchronisés et leur chemin a la priorité. |
| **`blacklist_whiteboards`** | Les cartes sur ces boards sont soustraites *avant* que tout contenu soit lu. La blacklist l'emporte sur la whitelist, donc une carte placée par erreur sur deux boards est quand même bloquée. |
| **Sous-whiteboards (non nommés)** | Déplacer une carte dans un sous-whiteboard change son `whiteboard_id`, donc un scan de surface ne la voit jamais. Exclue par structure, pas par une règle à mémoriser. |

La garantie en une ligne : chaque requête qui touche le titre ou le contenu d'une carte est limitée aux ids de whiteboard en whitelist ou aux titres `card_map`. Le titre et le contenu d'une carte hors whitelist ne sont jamais chargés en mémoire.

Deux principes de conception en découlent. **L'exclusion structurelle l'emporte sur l'exclusion soustractive** : une carte que la requête ne peut pas atteindre est plus sûre qu'une carte filtrée après lecture. **La meilleure notification est celle dont on n'a pas besoin** : l'outil est conçu pour que vous n'ayez jamais à vous demander si une carte a fuité.

## Comparaison

| | HeptaSieve | CLI officiel Heptabase | Autres outils d'export |
|---|---|---|---|
| Modèle de confidentialité | Liste d'autorisation fail-closed | Fail-open (base de connaissances complète) | Export total |
| Sync locale continue | Oui (`launchd`, 15 min) | Lecture à la demande | Export unique |
| Lit la DB locale en direct | Oui | Variable | Nécessite souvent un fichier de sauvegarde |
| Markdown fidèle à la structure | Tableaux, listes, sections, vidéo | Variable | Variable |
| Routage par destination par board | Oui, chemins absolus inclus | Non | Non |

Ce n'est pas un remplacement complet de Heptabase, et "meilleur que l'officiel" ne tient que sur trois axes : confidentialité contrôlable, synchronisation locale continue et fidélité de structure. Le public cible est intentionnellement restreint : les utilisateurs macOS qui vivent dans Heptabase et s'intéressent à ce qu'une IA peut voir. Si c'est vous, cet outil est fait exactement pour votre cas.

## Installation

Prérequis : macOS, Python 3.9+, l'application desktop Heptabase installée.

```bash
git clone https://github.com/yyu0310/heptasieve.git
cd heptasieve
cp config.example.json config.json
```

Modifiez ensuite `config.json` (chaque champ a un commentaire inline qui l'explique) :

1. Confirmez que `db_path` pointe vers votre `hepta.db` local.
2. Définissez `base_output_dir` et `board_output_dir` à l'emplacement où vous voulez écrire le Markdown.
3. Listez les whiteboards à exporter sous `whitelist_whiteboards`.
4. Ajoutez les substitutions de chemin précises sous `card_map`.

Lancez d'abord une prévisualisation, qui n'écrit rien :

```bash
python3 heptabase_sync.py --dry
```

Quand le plan semble correct, exécutez-le pour de vrai :

```bash
python3 heptabase_sync.py
```

### Synchronisation automatique toutes les 15 minutes

```bash
cp com.example.heptasieve.plist ~/Library/LaunchAgents/
# éditez le fichier copié : définissez les chemins absolus et confirmez votre chemin python3
launchctl load ~/Library/LaunchAgents/com.example.heptasieve.plist
```

## L'utiliser avec un agent IA

HeptaSieve inclut des docs lisibles par les agents pour que vous puissiez le configurer en parlant à un agent de codage IA plutôt qu'en suivant des étapes manuellement :

- [`AGENTS.md`](AGENTS.md) et [`CLAUDE.md`](CLAUDE.md) : comment un agent doit raisonner et configurer cet outil.
- [`llms.txt`](llms.txt) : un index des docs pour les LLMs.
- [`skills/setup-heptasieve/`](skills/setup-heptasieve/) : un skill Claude Code qui guide toute la configuration en une seule requête.

Dirigez votre agent vers le dossier Markdown exporté, jamais vers `hepta.db`. Cette séparation est l'essentiel.

## Comment ça fonctionne

Voir [`ARCHITECTURE.md`](ARCHITECTURE.md) pour l'architecture : le flux de données, l'ordonnancement fail-closed dans `build_plan`, les tables de base de données qu'il lit et les invariants de confidentialité à préserver lors de la modification du code.

## Limitations et mises en garde honnêtes

- **Le schéma est fragile.** Cela dépend de la structure interne de la base de données de Heptabase. Une mise à jour de Heptabase peut le casser. C'est non officiel par nature.
- **Lire la DB en direct n'est pas officiellement approuvé.** Ça fonctionne bien en pratique et c'est en lecture seule, mais vous devez savoir que ce n'est pas une intégration prise en charge.
- **macOS uniquement.** Les chemins et la configuration `launchd` supposent macOS aujourd'hui.

## Licence

[MIT](LICENSE).
