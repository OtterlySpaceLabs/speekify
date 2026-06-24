# Release Runbook

## 1. Objectif

Runbook operationnel pour publier une nouvelle version de Speekify.

Depuis la migration vers la CI GitHub, la release est **construite et publiee par
GitHub Actions**, pas en local. Le workflow `.github/workflows/release.yml` se
declenche a la publication d'une Release GitHub et:

- construit le binaire macOS standalone (`--onedir`) sur un runner `macos-latest`
- attache `speekify-macos-arm64.tar.gz` a la Release
- regenere `Formula/speekify.rb` et le committe sur `main`

Le depot est desormais **public et unique** (`OtterlySpaceLabs/speekify`): le tap
Homebrew vit dans ce depot (`Formula/`), il n'y a plus de depot Homebrew separe
ni de build local.

Un agent execute la release avec seulement:

- le numero de version cible (`VERSION`, ex. `0.2.0`)
- la branche de travail (`WORK_BRANCH`, defaut `main`)
- les notes de version

Si aucune note n'est fournie, deriver un resume concis a partir des commits depuis
le tag precedent.

## 2. Prerequis

- `gh` authentifie avec le scope `repo`
- `uv` et `git` en local (pour le bump de version et les tests)
- Worktree propre

Verification:

```bash
gh auth status
git status --short
```

## 3. Fichiers a mettre a jour avant la release

- `pyproject.toml` : champ `[project].version`
- `uv.lock` : entree `[[package]]` du package local `speekify`
- `README.md` / docs : seulement si le comportement utilisateur a change

`Formula/speekify.rb` n'est **pas** edite a la main : la CI le regenere.

Controle:

```bash
rg -n "version = \"${VERSION}\"" pyproject.toml uv.lock
```

## 4. Etapes

```bash
export VERSION="0.2.0"
export WORK_BRANCH="main"
export TAG="v${VERSION}"

# 1. Validation locale
uv sync --group dev
uv run pytest
uv run ruff check .

# 2. Bump + push
git add pyproject.toml uv.lock
git commit -m "chore(release): bump version to ${VERSION}"
git push origin "$WORK_BRANCH"

# 3. Tag + Release (declenche publish.yml ET release.yml)
git tag "$TAG"
git push origin "$TAG"
GH_PAGER=cat gh release create "$TAG" \
  --title "Speekify v${VERSION}" \
  --notes "<notes de release>"
```

La publication de la Release declenche :

- `publish.yml` → build wheel/sdist + publication PyPI
- `release.yml` → build macOS + upload de l'archive + commit de `Formula/speekify.rb` sur `main`

Aucune action macOS locale n'est requise.

## 5. Suivi de la CI

```bash
GH_PAGER=cat gh run list --workflow release.yml --limit 1
GH_PAGER=cat gh run watch <run-id>
```

Resultat attendu :

- `publish.yml` vert (PyPI)
- `release.yml` vert : archive attachee a la Release, `Formula/speekify.rb` mis a
  jour sur `main` (nouveau commit `chore(release): update Homebrew formula ...`)

## 6. Verifications post-publication

```bash
GH_PAGER=cat gh release view "$TAG"

# Telechargement public direct
TMPDIR="$(mktemp -d /tmp/speekify-release-check.XXXXXX)"
cd "$TMPDIR"
curl -L -o speekify.tar.gz \
  "https://github.com/OtterlySpaceLabs/speekify/releases/download/${TAG}/speekify-macos-arm64.tar.gz"
tar -xzf speekify.tar.gz
./speekify/speekify --help >/dev/null
./speekify/speekify setup --help >/dev/null

# Homebrew (tap explicite car le depot n'est pas nomme homebrew-*)
brew tap otterlyspacelabs/speekify https://github.com/OtterlySpaceLabs/speekify || true
git -C "$(brew --repo otterlyspacelabs/speekify)" pull --ff-only
HOMEBREW_NO_AUTO_UPDATE=1 brew fetch --force --formula otterlyspacelabs/speekify/speekify
```

Attendu :

- le SHA256 du telechargement correspond a celui de la formule
- `brew fetch` reussit sans installer/desinstaller

## 7. Rollback

```bash
GH_PAGER=cat gh release delete "$TAG" --yes || true
git tag -d "$TAG" || true
git push origin ":refs/tags/${TAG}" || true
```

Si le commit de formule sur `main` est mauvais, le revert comme tout autre commit.
Les releases PyPI sont immuables : un upload PyPI casse exige une nouvelle version.

## 8. Points de vigilance

- Ne pas editer `Formula/speekify.rb` a la main : la CI ecrase le fichier.
- `release.yml` pousse le commit de formule sur `main` avec `GITHUB_TOKEN`. Si
  `main` a une protection bloquant le bot Actions, l'etape de push echoue —
  autoriser le bot ou assouplir la regle.
- Build `arm64` uniquement (runner `macos-latest` = Apple Silicon).
- Le binaire est non signe : premier lancement = scan Gatekeeper unique.
```
