#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=/opt/woniunote-iter21-runtime
if [ "${ITER21_FIXTURE_WRONG_CSS_BODY_ONCE:-0}" = 1 ] && \
   [ "${1:-}" = start ] && [ "${2:-}" = woniunote ] && \
   [ ! -e "${ITER21_DATA:?fixture data path missing}/wrong-css-body-injected" ]; then
    index="$ITER21_STATE/current/frontend/dist/index.html"
    css_ref="$(grep -Eo 'href="/assets/[^" ]+\.css"' "$index" | head -1 | sed 's/^href="//; s/"$//')"
    [ -n "$css_ref" ] || { printf 'fixture CSS reference missing during wrong-body injection\n' >&2; exit 1; }
    css_file="$ITER21_STATE/assets/${css_ref#/assets/}"
    [ -f "$css_file" ] && [ ! -L "$css_file" ] || { printf 'fixture CSS asset missing during wrong-body injection\n' >&2; exit 1; }
    cp -p "$css_file" "$ITER21_DATA/wrong-css-body-original"
    printf '%s\n' "$css_file" > "$ITER21_DATA/wrong-css-body-path"
    printf '<!doctype html><html><body>fixture SPA fallback instead of CSS</body></html>\n' > "$css_file"
    touch "$ITER21_DATA/wrong-css-body-injected"
fi
if [ "${ITER21_PAUSE_BEFORE_CANDIDATE_START:-0}" = 1 ] && \
   [ "${1:-}" = start ] && [ "${2:-}" = woniunote ]; then
    marker="${ITER21_PAUSE_MARKER:?pause marker path missing}"
    touch "$marker"
    while [ ! -e "${marker}.continue" ]; do sleep 0.05; done
fi

if [ "${ITER21_REAL_SYSTEMD:-real}" = adapter ]; then
    "$ROOT/systemctl-adapter.sh" "$@"
else
    /usr/bin/systemctl "$@"
fi
