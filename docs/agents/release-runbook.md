# Release Runbook

## 1. Objectif du document

Ce document est le runbook operationnel de reference pour publier une nouvelle version de Speekify.

Il doit permettre a un futur agent IA d'executer la release de bout en bout avec seulement:

- le numero de version cible
- la branche de travail
- les notes de version a publier, si elles ne peuvent pas etre derivees des commits

Le workflow canonique de ce depot est un workflow manuel, reproductible, construit localement sur macOS, puis publie dans deux depots GitHub:

- le depot source prive `OtterlySpaceLabs/speekify`
- le depot Homebrew public `OtterlySpaceLabs/homebrew-speekify`

L'asset public distribue aux utilisateurs et a Homebrew doit toujours provenir de la release publique du tap Homebrew, pas de la release privee du depot source.

## 2. Informations requises avant de commencer

Renseigner ces variables avant toute action:

- `VERSION`: numero de version cible, par exemple `0.0.3`
- `WORK_BRANCH`: branche source a publier, par defaut `main`
- `SOURCE_RELEASE_NOTES`: note de release concise, orientee utilisateur, pour la release du depot source

Informations derives automatiquement a partir de `VERSION`:

- `TAG=v${VERSION}`
- `TAP_RELEASE_TAG=speekify-v${VERSION}`
- `SOURCE_RELEASE_TITLE=Speekify v${VERSION}`
- `TAP_RELEASE_TITLE=Speekify v${VERSION}`

Si aucune note de version n'est fournie, l'agent doit deriver un resume concis a partir des commits depuis le tag precedent, puis le faire valider si le resultat est ambigu.

## 3. Prerequis techniques

- Machine macOS avec la meme architecture que l'archive publiee, actuellement `arm64`
- Acces en lecture/ecriture aux deux depots GitHub
- `gh` authentifie avec les scopes `repo` et `workflow`
- `uv`, `git`, `curl`, `tar`, `shasum` et `brew` installes localement
- Depot source ouvert a sa racine
- Depot Homebrew disponible localement dans le dossier parent, sous `../homebrew-speekify`
- Worktrees propres, hors artefacts ignores

Commandes de verification:

```bash
gh auth status
cd /path/to/speekify
test -d ../homebrew-speekify
git status --short
cd ../homebrew-speekify
git status --short
```

## 4. Etapes de preparation

Depuis la racine du depot source, definir les variables de travail:

```bash
export VERSION="0.0.3"
export WORK_BRANCH="main"
export TAG="v${VERSION}"
export SOURCE_REPO="$PWD"
export TAP_REPO="$(cd .. && pwd)/homebrew-speekify"
export ARCH="$(uname -m)"
export ARCHIVE_NAME="speekify-macos-${ARCH}.tar.gz"
export ARCHIVE_PATH="$SOURCE_REPO/dist/${ARCHIVE_NAME}"
export TAP_RELEASE_TAG="speekify-v${VERSION}"
export SOURCE_RELEASE_TITLE="Speekify v${VERSION}"
export TAP_RELEASE_TITLE="Speekify v${VERSION}"
export TAP_RELEASE_NOTES="Public binary release for Homebrew install"
export PUBLIC_ASSET_URL="https://github.com/OtterlySpaceLabs/homebrew-speekify/releases/download/${TAP_RELEASE_TAG}/${ARCHIVE_NAME}"
export RELEASE_NOTES_FILE="$SOURCE_REPO/dist/release-notes-${VERSION}.md"
```

Creer le fichier de notes de release source:

```bash
mkdir -p "$SOURCE_REPO/dist"
cat > "$RELEASE_NOTES_FILE" <<'EOF'
<remplacer par des notes de release courtes, concretes et orientees utilisateur>
EOF
```

Verifier aussi le tag precedent, utile pour revoir les changements inclus:

```bash
git --no-pager tag --list
git --no-pager log --oneline --decorate "$(git describe --tags --abbrev=0)..HEAD"
```

## 5. Fichiers a mettre a jour

Mettre a jour ces fichiers dans le depot source avant toute publication:

- `pyproject.toml`: champ `[project].version`
- `uv.lock`: entree `[[package]]` du package local `speekify`

Mettre a jour ces fichiers seulement si le comportement visible par l'utilisateur a change:

- `README.md`
- documentation utilisateur ou notes techniques liees a la release

Le fichier du tap Homebrew n'est pas edite a la main au debut du workflow. Il est regenere plus tard par script:

- `../homebrew-speekify/Formula/speekify.rb`

Controles apres edition:

```bash
rg -n "version = \"${VERSION}\"" pyproject.toml uv.lock
uv run python -c "import importlib.metadata as m; print(m.version('speekify'))"
```

## 6. Commandes a executer

Sequence complete a executer, dans cet ordre:

```bash
cd "$SOURCE_REPO"
uv sync --group dev
uv run pytest
uv run ruff check .

git add pyproject.toml uv.lock
# Ajouter explicitement ici tout autre fichier voulu pour cette release.
git commit -m "Bump version to ${VERSION}"
git push origin "$WORK_BRANCH"

./scripts/build_standalone_macos.sh
SHA256="$(shasum -a 256 "$ARCHIVE_PATH" | awk '{print $1}')"

git tag "$TAG"
git push origin "$TAG"

RUN_ID="$(GH_PAGER=cat gh run list --repo OtterlySpaceLabs/speekify --workflow release.yml --limit 10 --json databaseId,headBranch,status --jq '.[] | select(.headBranch == env.TAG) | .databaseId' | head -n 1)"
if [[ -n "$RUN_ID" ]]; then gh run cancel "$RUN_ID" --repo OtterlySpaceLabs/speekify; fi

GH_PAGER=cat gh release create "$TAG" "$ARCHIVE_PATH" \
  --repo OtterlySpaceLabs/speekify \
  --title "$SOURCE_RELEASE_TITLE" \
  --notes-file "$RELEASE_NOTES_FILE"

GH_PAGER=cat gh release create "$TAP_RELEASE_TAG" "$ARCHIVE_PATH" \
  --repo OtterlySpaceLabs/homebrew-speekify \
  --title "$TAP_RELEASE_TITLE" \
  --notes "$TAP_RELEASE_NOTES"

uv run python scripts/render_homebrew_formula.py \
  --version "$VERSION" \
  --url "$PUBLIC_ASSET_URL" \
  --sha256 "$SHA256" \
  --homepage https://github.com/OtterlySpaceLabs/speekify \
  --output "$TAP_REPO/Formula/speekify.rb"

cd "$TAP_REPO"
git add Formula/speekify.rb
git commit -m "Update speekify formula to ${VERSION}"
git push origin main
```

## 7. Verifications locales

Avant toute publication distante, les verifications locales minimales sont:

```bash
cd "$SOURCE_REPO"
uv run pytest
uv run ruff check .
test -f "$ARCHIVE_PATH"
shasum -a 256 "$ARCHIVE_PATH"
./dist/speekify --help >/dev/null
./dist/speekify setup --help >/dev/null
```

Resultat attendu:

- les tests passent
- Ruff passe
- l'archive existe dans `dist/`
- le binaire local repond a `--help` et `setup --help`

## 8. Commit de release

Le commit de release dans le depot source doit contenir au minimum le bump de version.

Commande standard:

```bash
cd "$SOURCE_REPO"
git add pyproject.toml uv.lock
git commit -m "Bump version to ${VERSION}"
git push origin "$WORK_BRANCH"
```

Si des changements de documentation ou de comportement utilisateur font partie de la release, ils peuvent etre inclus dans le meme commit si cela reste lisible et volontaire.

## 9. Creation du tag de version

Creer le tag local uniquement apres:

- un `main` pousse
- une build locale reussie
- un SHA256 connu

Commandes:

```bash
cd "$SOURCE_REPO"
git tag "$TAG"
git push origin "$TAG"
```

Important: le depot source possede un workflow GitHub Actions declenche sur `push` de tag. Si ce run demarre alors que la release est faite manuellement, il faut l'annuler pour eviter des assets ou releases en conflit.

Commande type:

```bash
GH_PAGER=cat gh run list --repo OtterlySpaceLabs/speekify --workflow release.yml --limit 5 --json databaseId,status,headBranch,displayTitle
gh run cancel <databaseId> --repo OtterlySpaceLabs/speekify
```

Annuler uniquement la run dont `headBranch` vaut `vX.Y.Z`.

## 10. Push vers le depot distant

Les pushes distants a effectuer pendant une release sont:

1. push de la branche source:

```bash
cd "$SOURCE_REPO"
git push origin "$WORK_BRANCH"
```

2. push du tag source:

```bash
git push origin "$TAG"
```

3. push de la formule dans le tap Homebrew:

```bash
cd "$TAP_REPO"
git push origin main
```

Ne jamais considerer la release terminee tant que les deux depots n'ont pas recu leur push respectif.

## 11. Publication ou declenchement de la release

La publication canonique est manuelle et se fait en quatre sous-etapes:

1. construire localement l'archive avec `./scripts/build_standalone_macos.sh`
2. creer la release source privee `vX.Y.Z` dans `OtterlySpaceLabs/speekify`
3. creer la release publique `speekify-vX.Y.Z` dans `OtterlySpaceLabs/homebrew-speekify`
4. regenerer puis publier la formule Homebrew

Commandes de publication:

```bash
cd "$SOURCE_REPO"
GH_PAGER=cat gh release create "$TAG" "$ARCHIVE_PATH" \
  --repo OtterlySpaceLabs/speekify \
  --title "$SOURCE_RELEASE_TITLE" \
  --notes-file "$RELEASE_NOTES_FILE"

GH_PAGER=cat gh release create "$TAP_RELEASE_TAG" "$ARCHIVE_PATH" \
  --repo OtterlySpaceLabs/homebrew-speekify \
  --title "$TAP_RELEASE_TITLE" \
  --notes "$TAP_RELEASE_NOTES"

uv run python scripts/render_homebrew_formula.py \
  --version "$VERSION" \
  --url "$PUBLIC_ASSET_URL" \
  --sha256 "$SHA256" \
  --homepage https://github.com/OtterlySpaceLabs/speekify \
  --output "$TAP_REPO/Formula/speekify.rb"

cd "$TAP_REPO"
git add Formula/speekify.rb
git commit -m "Update speekify formula to ${VERSION}"
git push origin main
```

Utiliser `uv run python`, pas `python`, pour regenerer la formule. L'environnement local peut ne pas exposer `python` directement.

## 12. Verifications post-publication

Apres publication, verifier les deux releases GitHub, le telechargement public direct et le flux Homebrew reel.

Verification des releases:

```bash
GH_PAGER=cat gh release view "$TAG" --repo OtterlySpaceLabs/speekify
GH_PAGER=cat gh release view "$TAP_RELEASE_TAG" --repo OtterlySpaceLabs/homebrew-speekify
```

Smoke test de l'archive publique:

```bash
TMPDIR="$(mktemp -d /tmp/speekify-release-check.XXXXXX)"
cd "$TMPDIR"
curl -L -o speekify.tar.gz "$PUBLIC_ASSET_URL"
shasum -a 256 speekify.tar.gz
tar -xzf speekify.tar.gz
./speekify --help >/dev/null
./speekify setup --help >/dev/null
```

Verification du tap Homebrew public sans modifier l'installation locale:

```bash
HOMEBREW_NO_AUTO_UPDATE=1 brew audit --strict --formula "$TAP_REPO/Formula/speekify.rb"
HOMEBREW_NO_AUTO_UPDATE=1 brew fetch --formula "$TAP_REPO/Formula/speekify.rb"
```

Resultat attendu:

- le SHA256 du telechargement public correspond a celui de l'archive locale publiee
- la formule Homebrew passe `brew audit --strict`
- `brew fetch` reussit sur la formule publiee sans installer ni desinstaller `speekify`

## 13. Checklist finale

- [ ] `VERSION`, `WORK_BRANCH` et les notes de version sont definis
- [ ] `pyproject.toml` contient la bonne version
- [ ] `uv.lock` contient la bonne version pour le package local `speekify`
- [ ] `uv run pytest` passe
- [ ] `uv run ruff check .` passe
- [ ] l'archive locale `dist/${ARCHIVE_NAME}` existe
- [ ] le SHA256 de l'archive a ete capture
- [ ] la branche source a ete poussee
- [ ] le tag `vX.Y.Z` a ete cree et pousse
- [ ] la run GitHub Actions declenchee par le tag a ete annulee si la publication est manuelle
- [ ] la release source `vX.Y.Z` existe et contient l'archive
- [ ] la release publique `speekify-vX.Y.Z` existe et contient l'archive
- [ ] `Formula/speekify.rb` pointe vers l'URL publique correcte et le bon SHA256
- [ ] la formule Homebrew a ete committee et poussee dans le tap public
- [ ] le telechargement public direct fonctionne
- [ ] la formule Homebrew passe `brew audit --strict` et `brew fetch` sans modifier l'installation locale

## 14. Procedure de rollback ou points de vigilance

### Rollback minimal si la release est invalide

Si la publication a echoue ou si les assets publies sont mauvais, supprimer d'abord les releases GitHub, puis corriger localement, puis recommencer.

Commandes de nettoyage:

```bash
GH_PAGER=cat gh release delete "$TAG" --repo OtterlySpaceLabs/speekify --yes || true
GH_PAGER=cat gh release delete "$TAP_RELEASE_TAG" --repo OtterlySpaceLabs/homebrew-speekify --yes || true
git tag -d "$TAG" || true
git push origin ":refs/tags/${TAG}" || true
```

Si le tag avait ete pousse sur le mauvais commit, le recreer apres correction:

```bash
git tag "$TAG"
git push origin "$TAG"
```

### Points de vigilance obligatoires

- Ne pas publier la formule Homebrew avant d'avoir l'URL publique finale et le SHA256 final.
- Ne pas compter sur GitHub Actions comme source d'archive canonique pour cette procedure. La build manuelle locale est la reference.
- Annuler toute run `release.yml` declenchee par le tag si l'on suit ce runbook manuel.
- Le tap public et le depot source sont deux depots distincts; chacun doit etre committe et pousse separement.
- La build PyInstaller peut generer `build/` et `speekify.spec`; ces artefacts sont locaux et ne doivent pas etre commites.
- Utiliser les URLs `OtterlySpaceLabs/...`, pas les anciennes URLs `hiboux/...`.