# Audit du projet Speekify

Audit technique complet réalisé le 11 juin 2026 en préparation de la prochaine release (version actuelle : 0.0.6). L'audit a comparé la documentation (README, SPECS, docs/, man page), le code source, les configurations, les scripts et les tests, puis a vérifié l'utilisabilité réelle des fonctionnalités, y compris par des extractions réseau en conditions réelles.

## Résumé exécutif

**État général du projet** : sain dans l'ensemble. L'architecture est propre et cohérente avec la documentation, la suite de tests passe intégralement (100 tests après audit), `ruff check` passe, et les chemins critiques (CLI, extraction d'articles, YouTube, dry-run/inspect, feed RSS, serveur MCP stdio) fonctionnent réellement. Deux problèmes sérieux ont été identifiés et corrigés : un faux positif silencieux sur l'extraction X/Twitter (génération d'un WAV contenant la page d'erreur « JavaScript is not available ») et une incompatibilité avec typer ≥ 0.26 qui cassait la gestion d'erreurs CLI et la config utilisateur hors environnement verrouillé.

**Niveau de préparation de la release** : bon, avec une action obligatoire — reconstruire le binaire standalone macOS (le binaire actuel dans `dist/` affiche `unknown` pour `--version`, le script de build est corrigé mais l'archive doit être regénérée sur macOS).

| Indicateur | Valeur |
|---|---|
| Fonctionnalités vérifiées | 20 |
| Problèmes corrigés | 9 |
| Fonctionnalités validées pour la release | 15 |
| Fonctionnalités incomplètes | 3 |
| Fonctionnalités bloquant la release | 1 (binaire standalone à reconstruire) |

Résultats de validation après corrections : `pytest` 100/100 ✅ (98 avant audit, dont 1 test fragile réparé, + 2 tests ajoutés), `ruff check .` ✅, `uv.lock` resynchronisé sans changement de version d'aucun paquet.

## Corrections effectuées

### 1. Extraction X/Twitter : faux positif silencieux (bug majeur)

- **Fichiers** : `src/speekify/extractors/x.py`, `src/speekify/extract.py`
- **Problème identifié** : preuve concrète dans le dépôt — le sidecar `javascript-is-not-available-20260611-131823.json` à la racine montre qu'une URL d'article X (`x.com/w1nklerr/article/…`) a généré le 11 juin un WAV de 35 s lisant la page d'erreur « JavaScript is not available ». Deux causes : (a) le motif `looks_like_x_status_url` reconnaissait `/status/` et `/i/article/` mais pas `/{user}/article/{id}`, donc l'oEmbed était sauté ; (b) quand l'oEmbed échouait ou renvoyait un texte trop court, le code retombait sur le fetch HTML générique de x.com, qui sert systématiquement une page d'erreur exigeant JavaScript (vérifié en conditions réelles : oEmbed = 404 pour les articles X, x.com = page d'erreur de 276 ko). Un test couvrant ce cas (`test_extract_url_rejects_x_article_shell_fallback`, visible dans `.pytest_cache/v/cache/lastfailed`) a existé puis a disparu sans que le bug soit corrigé.
- **Correction appliquée** : le motif reconnaît désormais `/{user}/article/{id}` ; pour toute URL X reconnue, si l'oEmbed ne fournit pas de texte exploitable, une `ValueError` explicite est levée au lieu de retomber sur le fetch HTML de x.com. Deux tests unitaires ajoutés dans `tests/test_extract.py`.
- **Impact** : plus aucun WAV poubelle généré silencieusement depuis une URL X ; l'utilisateur reçoit une erreur claire. Vérifié en conditions réelles après correction.

### 2. Compatibilité typer non bornée + dépendance click non déclarée

- **Fichiers** : `pyproject.toml`, `uv.lock`
- **Problème identifié** : `__main__.py` importe `click` directement (gestion d'erreurs CLI, `ParameterSource` pour la config utilisateur) mais `click` n'était pas déclaré comme dépendance, et `typer>=0.12` était sans borne supérieure. Démonstration dans cet audit : avec typer 0.26.x (qui embarque son propre click sous `typer._click` et, en 0.26.0, ne dépend plus du paquet `click`), 3 tests échouent — les erreurs de paramètres CLI ne sont plus interceptées et la config utilisateur est ignorée. Toute installation fraîche hors `uv.lock` (pip, bump de lock) cassait la CLI.
- **Correction appliquée** : `typer>=0.12,<0.26` (avec commentaire expliquant la raison) et ajout de `click>=8.1` ; `uv lock` régénéré — diff minimal vérifié, aucune version de paquet modifiée (typer reste en 0.25.1, click en 8.4.0).
- **Impact** : les installations hors lock restent fonctionnelles ; le risque de casse silencieuse à la prochaine mise à jour de dépendances est éliminé.

### 3. `speekify --version` cassé dans le binaire standalone

- **Fichier** : `scripts/build_standalone_macos.sh`
- **Problème identifié** : le bundle PyInstaller n'inclut pas les métadonnées de distribution de speekify (vérifié par inspection du binaire `dist/speekify` : aucune `speekify-*.dist-info` embarquée). `importlib.metadata.version("speekify")` échoue donc et `--version` affiche `unknown` dans le binaire distribué via Homebrew. Le test de la formule Homebrew (`assert_match "<version>"` sur `--version`) échouerait à `brew test`.
- **Correction appliquée** : ajout de `--copy-metadata speekify` à l'invocation PyInstaller.
- **Impact** : les prochains builds standalone afficheront la vraie version. ⚠️ Nécessite de reconstruire l'archive sur macOS (voir « Fonctionnalités bloquant la release »).

### 4. Référence obsolète `--collect-all textual` dans le build

- **Fichier** : `scripts/build_standalone_macos.sh`
- **Problème identifié** : `textual` a été retiré des dépendances le 28 mai 2026 (commit c9c5da1 « remove TUI ») mais le script de build collectait toujours ce paquet inexistant (warning PyInstaller à chaque build, vérifié avec PyInstaller 6.20 : non bloquant mais trompeur).
- **Correction appliquée** : ligne supprimée.
- **Impact** : build plus propre, plus de référence à une dépendance disparue.

### 5. Homepage par défaut obsolète dans le rendu de formule Homebrew

- **Fichier** : `scripts/render_homebrew_formula.py`
- **Problème identifié** : valeur par défaut `https://github.com/hiboux/speekify` alors que le runbook de release exige explicitement « Utiliser les URLs OtterlySpaceLabs/…, pas les anciennes URLs hiboux/… ».
- **Correction appliquée** : défaut remplacé par `https://github.com/OtterlySpaceLabs/speekify`.
- **Impact** : une exécution du script sans `--homepage` ne produit plus une formule pointant vers le mauvais dépôt.

### 6. Test CLI non déterministe (dépendant de la largeur du terminal)

- **Fichier** : `tests/test_cli.py` (`test_main_rejects_invalid_feed_base_url`)
- **Problème identifié** : le test vérifiait une sous-chaîne de 50 caractères dans un panneau Rich ; dès que le terminal est étroit (reproduit avec `COLUMNS=60`), Rich insère un retour à la ligne dans le message et l'assertion échoue. Ce test figure dans le `lastfailed` du cache pytest du dépôt : il a réellement échoué lors d'une exécution précédente sur la machine de développement.
- **Correction appliquée** : largeur de la console d'erreur fixée à 200 pendant le test (via `monkeypatch` sur `error_console._width`, robuste avec rich 15 qui fige la largeur à la construction). Vérifié : le test passe désormais aussi sous `COLUMNS=60`.
- **Impact** : suite de tests déterministe quel que soit le terminal (local, CI).

### 7. Options CLI non documentées (`--english-islands`, `--english-lexicon-path`)

- **Fichiers** : `README.md`, `docs/man/speekify.1`, `SPECS.md`
- **Problème identifié** : ces deux options existent dans le CLI et dans la config utilisateur TOML (`english_islands`, `english_lexicon_path`) mais étaient absentes de la table des options du README, de la man page et des specs (mentionnées uniquement côté MCP).
- **Correction appliquée** : ajout dans la table d'options du README, dans l'exemple de config TOML, dans MAIN OPTIONS de la man page et dans les Runtime Decisions de SPECS.md.
- **Impact** : documentation alignée sur le CLI réel.

### 8. Documentation X/Twitter trompeuse

- **Fichiers** : `README.md`, `SPECS.md`, `docs/agents/dependencies-integrations.md`
- **Problème identifié** : la documentation annonçait la prise en charge des « X/Twitter posts » sans réserve, alors que seuls les posts publics exposés via l'oEmbed public fonctionnent ; les articles X, comptes protégés et posts très courts ne sont pas extractibles sans session connectée.
- **Correction appliquée** : limites documentées explicitement aux trois endroits (et description du non-fallback vers x.com dans la doc agents).
- **Impact** : les attentes des utilisateurs correspondent au comportement réel.

### 9. Architecture documentée incomplète dans SPECS.md

- **Fichier** : `SPECS.md`
- **Problème identifié** : `multilingual.py` (segmentation îlots anglais), `metadata.py` (sidecars + RSS) et `mcp_server.py` n'apparaissaient pas dans la section Architecture alors qu'ils portent des fonctionnalités documentées ailleurs.
- **Correction appliquée** : trois lignes ajoutées à la section Architecture.
- **Impact** : SPECS.md reflète l'arborescence réelle.

## Fonctionnalités validées pour la release

Chaque fonctionnalité ci-dessous a été confirmée par les tests automatisés et, quand c'était possible dans l'environnement d'audit, par une exécution réelle.

1. **Génération texte inline → WAV** — pipeline complet couvert par les tests ; WAV réels récents présents dans le dépôt (générés les 28 mai et 11 juin).
2. **Entrée stdin (pipe)** — couvert par les tests CLI.
3. **Extraction d'article HTML générique (trafilatura)** — vérifiée en conditions réelles pendant l'audit (article extrait : 9 692 caractères, titre correct).
4. **Extraction de transcripts YouTube (anglais)** — vérifiée en conditions réelles pendant l'audit sur l'URL d'exemple du README (19 263 caractères extraits, titre correct).
5. **Traduction automatique EN→FR avant synthèse** — couverte par les tests ; preuve d'exécution réelle réussie le 11 juin (sidecar `how-long-contexts-fail-…` : article anglais → 10 minutes d'audio français, 43 batchs).
6. **Tagging vocal (`<breath>`, `<sigh>`, sentiment CardiffNLP avec fail-open)** — couvert par les tests ; le fail-open vers les règles seules a été vérifié en exécution réelle (sans torch, le dry-run aboutit avec « Sentiment: not used »).
7. **Îlots anglais en synthèse française (`--english-islands`, lexique personnalisé)** — couvert par les tests ; désormais documenté.
8. **`--dry-run` / `speekify inspect`** — exécutés réellement pendant l'audit, panneau de prévisualisation correct.
9. **`speekify feed rebuild` / `feed validate`** — `validate` exécuté réellement (3 entrées détectées, 0 invalide) ; `rebuild` couvert par les tests.
10. **Sidecars JSON + flux RSS podcast (`speekify-feed.xml`, `--feed-base-url`)** — couverts par les tests ; fichiers réels conformes au schéma présents dans le dépôt.
11. **Config utilisateur TOML (`~/.config/speekify/config.toml`, `SPEEKIFY_CONFIG`)** — couverte par les tests (y compris priorité CLI > config > défauts).
12. **`speekify setup` (warmup des modèles, `--skip-translation`, `--skip-sentiment`)** — logique couverte par les tests ; le téléchargement réel des modèles dépend de Hugging Face et a fonctionné sur la machine de développement (WAV récents en attestent).
13. **`speekify --doctor`** — couvert par les tests (runtime, dépendances, chargement des modèles).
14. **Serveur MCP en stdio (`speekify-mcp`)** — handshake MCP réel exécuté pendant l'audit : initialisation OK, les deux outils documentés (`speekify_generate_wav`, `speekify_generation_defaults`) sont bien exposés, plus le prompt `news_recap_to_audio`. Les fichiers d'exemple `.mcp.json`, `.vscode/mcp.json`, `.codex/config.toml.example` sont cohérents avec la doc.
15. **Logging (`logs/speekify.log`) avec rétention 14 jours** — couvert par les tests.

## Fonctionnalités incomplètes

### 1. Extraction X/Twitter — partiellement fonctionnelle

- **Description** : extraction du texte d'un post X via l'endpoint oEmbed public.
- **Raison du blocage** : x.com ne sert aucun contenu aux clients HTTP sans JavaScript ni session. Seul l'oEmbed public fonctionne, et uniquement pour les posts publics dont le texte est suffisant. Les articles X renvoient 404 sur l'oEmbed (vérifié en réel). Constat supplémentaire : l'oEmbed est instable pour les tweets qui ne contiennent qu'un lien (la carte d'article est parfois incluse, parfois non — observé en réel sur l'URL d'exemple du README, qui est précisément un tweet-lien de 58 caractères et échoue donc la plupart du temps).
- **Ce qui manque** : gestion de session/authentification X (cookies ou API authentifiée) pour les articles, posts protégés et posts courts. Conformément au périmètre de l'audit, cette fonctionnalité n'a pas été développée ; le comportement cassé silencieux a été remplacé par une erreur explicite.
- **Effort estimé** : Important.

### 2. Fallback Medium (flux RSS + GraphQL) — validé par tests uniquement

- **Description** : récupération d'articles Medium bloqués (401/403/429) via le flux RSS de la publication puis l'API GraphQL.
- **Raison du blocage** : couvert par des tests unitaires complets, mais aucune vérification en conditions réelles n'a pu être faite pendant l'audit (nécessite un article Medium effectivement bloqué). Les protections anti-bot de Medium évoluent vite ; en application du principe « en cas de doute, non validée », cette fonctionnalité reste à confirmer manuellement.
- **Ce qui manque** : un test manuel sur 2–3 URL Medium membres réelles avant d'annoncer la fonctionnalité dans les notes de release.
- **Effort estimé** : Faible (vérification manuelle).

### 3. Serveur MCP en streamable-http — non vérifié en exécution

- **Description** : `speekify-mcp --transport streamable-http` (documenté en détail dans `docs/mcp-clients.md`, y compris reverse proxy et tunnel ChatGPT).
- **Raison du blocage** : l'argument est transmis tel quel à FastMCP et le transport stdio fonctionne, mais le mode HTTP n'a pas été démarré/testé pendant l'audit. La doc (port 8000, chemin `/mcp`) repose sur les défauts de FastMCP, non revérifiés. La partie « OpenAI Secure MCP Tunnel / tunnel-client » documente un outillage tiers non testable depuis ce dépôt.
- **Ce qui manque** : un smoke test local (`curl` sur `http://127.0.0.1:8000/mcp`) avant de mettre en avant ce mode dans la release.
- **Effort estimé** : Faible.

## Fonctionnalités bloquant la release

1. **Binaire standalone macOS à reconstruire (bloquant)** : l'archive actuelle `dist/speekify-macos-arm64.tar.gz` (29 mai) a été construite avant les corrections — son `--version` affiche `unknown`, et le test de la formule Homebrew échouerait. Action : relancer `./scripts/build_standalone_macos.sh` sur macOS (le script corrigé embarque désormais les métadonnées), vérifier `./dist/speekify --version`, puis suivre le runbook. Sans cela, ne pas publier d'archive.

Aucun autre blocage : les bugs X et typer, qui auraient été bloquants, sont corrigés et testés.

## Incohérences documentation / code

Les incohérences 1 à 5 ont été corrigées pendant l'audit ; les suivantes sont signalées sans correction.

1. **Corrigée** — README/SPECS annonçaient la prise en charge X/Twitter sans mentionner que seuls les posts publics via oEmbed fonctionnent (les articles X généraient un WAV de page d'erreur).
2. **Corrigée** — `--english-islands` et `--english-lexicon-path` absents du README (table des options), de la man page et de l'exemple TOML alors qu'ils existent dans le code et la config utilisateur.
3. **Corrigée** — `SPECS.md` n'incluait pas `multilingual.py`, `metadata.py` ni `mcp_server.py` dans son architecture.
4. **Corrigée** — `docs/agents/dependencies-integrations.md` décrivait le fallback « oEmbed puis extraction générique » pour X, désormais inexact, et omettait la dépendance directe `click`.
5. **Corrigée** — `scripts/render_homebrew_formula.py` contredisait le runbook (URL `hiboux/` vs `OtterlySpaceLabs/`).
6. **Signalée** — l'exemple X du README (`x.com/w1nklerr/status/2060057563991884060`) est un tweet ne contenant qu'un lien : son extraction échoue la plupart du temps (désormais avec une erreur claire). Prévoir un exemple de post X au texte réel, vérifié, ou retirer l'exemple.
7. **Signalée** — les messages d'erreur d'extraction sont en français (`extract.py`, `extractors/youtube.py`) alors que tout le reste de l'interface est en anglais. Choix assumé possible (public cible francophone) mais incohérent.
8. **Signalée** — `docs/mcp-clients.md` documente longuement des intégrations tierces (tunnel OpenAI, Nginx/Caddy) qui ne sont pas vérifiables depuis ce dépôt ; à considérer comme « exemples indicatifs » plutôt que comme fonctionnalités du produit.

## Dette technique détectée

1. **`mcp_server._build_request`** : fonction utilisée uniquement par les tests (`generate_wav` appelle directement `build_generation_request`). Code quasi mort à fusionner ou à supprimer avec ses tests dédiés.
2. **`--dry-run`/`inspect` créent le répertoire de sortie** : `build_output_path` fait un `mkdir` même en prévisualisation. Effet de bord mineur mais surprenant pour un dry-run.
3. **Logs et sorties relatifs au répertoire courant** : `logs/speekify.log`, sidecars et `speekify-feed.xml` sont créés dans le CWD. Pour un binaire installé via Homebrew, cela éparpille des dossiers `logs/` partout où la commande est lancée. Comportement documenté, mais à reconsidérer (XDG state dir) après la release.
4. **`.gitignore` avec motif large `*-*.json`** : ignore les sidecars mais masquerait aussi tout futur fichier JSON légitime contenant un tiret. Préférer un motif plus ciblé (par ex. horodaté `*-[0-9]*.json`).
5. **Artefacts de travail à la racine du dépôt** : 3 sidecars JSON, `speekify-feed.xml`, WAV de tests (racine et `output/`), binaires dans `dist/` (198 Mo). Non versionnés, mais à nettoyer avant de packager la release pour éviter toute inclusion accidentelle.
6. **Nettoyage du texte oEmbed X perfectible** : les liens `t.co` et certains restes d'embed (« Article », compteurs) restent dans le texte synthétisé des posts X valides.
7. **`.codex/config.toml` réel versionné** en plus de `.codex/config.toml.example` : redondant, source de confusion sur le fichier de référence.
8. **Tests Rich sensibles au rendu** : plusieurs assertions reposent sur la sortie texte de panneaux Rich (un seul cas fragile corrigé). Une aide de test qui fixe la largeur de console pour toute la suite éviterait de futures régressions du même type.
9. **Le cache `.pytest_cache` versionné dans l'arbre de travail** garde la trace d'un test supprimé (`test_extract_url_rejects_x_article_shell_fallback`) — symptôme d'un test effacé au lieu d'être réparé. Le scénario est de nouveau couvert par les deux tests ajoutés.

## Recommandations

Uniquement orientées stabilité, qualité, cohérence et préparation de release :

1. **Avant de tagger** : reconstruire l'archive standalone sur macOS avec le script corrigé, vérifier `./dist/speekify --version`, `--help`, `setup --help`, puis dérouler le runbook (`docs/agents/release-runbook.md`). C'est le seul prérequis bloquant.
2. **Mentionner dans les notes de release** la nouvelle borne `typer<0.26` et le comportement corrigé des URLs X (erreur claire au lieu d'un WAV de page d'erreur), car le second change un comportement observable.
3. **Smoke tests manuels recommandés avant publication** (10 minutes) : une URL Medium membre (fallback feed/GraphQL), `speekify-mcp --transport streamable-http` + `curl /mcp`, et une génération complète `speekify "texte"` après `speekify setup` sur une machine propre.
4. **Ajouter `uv run pytest` + `uv run ruff check .` en CI sur chaque push** (le workflow actuel ne les exécute qu'au tag de release) pour détecter au plus tôt les dérives type typer 0.26.
5. **Stabiliser la suite de tests Rich** avec une fixture globale fixant la largeur de console, et supprimer `mcp_server._build_request` au profit d'appels directs à `build_generation_request` dans les tests.
6. **Nettoyer le dépôt avant packaging** (WAV/JSON/feed de tests à la racine, vieux binaires `dist/`), et envisager un motif `.gitignore` plus précis pour les sidecars.
7. **Après la release**, traiter les points de dette 2 et 3 (dry-run sans mkdir, emplacement des logs) qui touchent l'expérience utilisateur du binaire installé.
