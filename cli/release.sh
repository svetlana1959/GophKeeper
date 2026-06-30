#!/usr/bin/env bash
# Cut a goph release: bump the version, tag it, and push so the Release CLI
# workflow (.github/workflows/release-cli.yaml) builds and publishes via
# GoReleaser.
#
#   ./release.sh            # interactive
#   ./release.sh patch      # preselect the bump (patch | minor | major | vX.Y.Z)
#   ./release.sh v1.2.3 -y  # explicit version, skip the confirm prompt

set -euo pipefail

REPO_SLUG="svetlana1959/GophKeeper"

# --- helpers ---------------------------------------------------------------
die() { echo "error: $*" >&2; exit 1; }
ask() { # ask <prompt> <varname> [default]
	local prompt="$1" __var="$2" default="${3:-}" reply
	if [ -n "$default" ]; then prompt="$prompt [$default]"; fi
	read -r -p "$prompt: " reply || true
	printf -v "$__var" '%s' "${reply:-$default}"
}

# --- preflight -------------------------------------------------------------
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "not inside a git repository"

ASSUME_YES=0
BUMP_ARG=""
for arg in "$@"; do
	case "$arg" in
		-y|--yes) ASSUME_YES=1 ;;
		patch|minor|major) BUMP_ARG="$arg" ;;
		v[0-9]*) BUMP_ARG="$arg" ;;
		*) die "unknown argument: $arg" ;;
	esac
done

if [ -n "$(git status --porcelain)" ]; then
	die "working tree is not clean — commit or stash changes first"
fi

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
echo "Fetching latest tags..."
git fetch --tags --quiet origin

# --- figure out the current and next version -------------------------------
LATEST="$(git tag --list 'v*' --sort=-v:refname | head -n1)"
LATEST="${LATEST:-v0.0.0}"
echo "Latest release: $LATEST"

ver="${LATEST#v}"
IFS='.' read -r MAJOR MINOR PATCH <<<"$ver"
MAJOR="${MAJOR:-0}"; MINOR="${MINOR:-0}"; PATCH="${PATCH:-0}"

BUMP="$BUMP_ARG"
if [ -z "$BUMP" ]; then
	echo
	echo "  patch  -> v${MAJOR}.${MINOR}.$((PATCH + 1))"
	echo "  minor  -> v${MAJOR}.$((MINOR + 1)).0"
	echo "  major  -> v$((MAJOR + 1)).0.0"
	echo "  custom -> enter an explicit vX.Y.Z"
	ask "Bump type (patch/minor/major/custom)" BUMP "patch"
fi

case "$BUMP" in
	patch)  NEW="v${MAJOR}.${MINOR}.$((PATCH + 1))" ;;
	minor)  NEW="v${MAJOR}.$((MINOR + 1)).0" ;;
	major)  NEW="v$((MAJOR + 1)).0.0" ;;
	custom) ask "New version (vX.Y.Z)" NEW ;;
	v[0-9]*) NEW="$BUMP" ;;
	*) die "invalid bump type: $BUMP" ;;
esac

[[ "$NEW" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "invalid version: $NEW (expected vX.Y.Z)"
git rev-parse "$NEW" >/dev/null 2>&1 && die "tag $NEW already exists"

# --- release notes / tag message ------------------------------------------
ask "Release name/notes (optional)" MESSAGE "Release $NEW"

# --- confirm ---------------------------------------------------------------
echo
echo "  Branch:  $BRANCH"
echo "  Tag:     $NEW"
echo "  Message: $MESSAGE"
echo "  Commit:  $(git rev-parse --short HEAD) $(git log -1 --pretty=%s)"
echo
if [ "$BRANCH" != "main" ]; then
	echo "note: you are not on 'main'. The release builds whatever commit '$NEW' points to."
fi
if [ "$ASSUME_YES" -ne 1 ]; then
	ask "Proceed? (y/N)" CONFIRM "n"
	case "$CONFIRM" in y|Y|yes|YES) ;; *) die "aborted" ;; esac
fi

# --- push branch, then the tag (the tag is what triggers the release) ------
echo "Pushing $BRANCH..."
git push origin "$BRANCH"

echo "Creating and pushing tag $NEW..."
git tag -a "$NEW" -m "$MESSAGE"
git push origin "$NEW"

echo
echo "Done. Release workflow: https://github.com/${REPO_SLUG}/actions"
echo "Once green: https://github.com/${REPO_SLUG}/releases/tag/${NEW}"
