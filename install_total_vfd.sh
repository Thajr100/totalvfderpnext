#!/usr/bin/env bash
# Total VFD — one-command installer for ERPNext (run from your bench folder or anywhere)
set -e

APP_NAME="total_vfd"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_SOURCE="${SCRIPT_DIR}/total_vfd"

bold() { printf "\033[1m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
yellow() { printf "\033[33m%s\033[0m\n" "$*"; }
red() { printf "\033[31m%s\033[0m\n" "$*"; }

bold "=========================================="
bold "  Total VFD — Easy installer for ERPNext"
bold "=========================================="
echo ""

# Find bench
BENCH_DIR=""
if command -v bench >/dev/null 2>&1 && [ -f "sites/common_site_config.json" ]; then
	BENCH_DIR="$(pwd)"
elif [ -n "${BENCH_PATH:-}" ] && [ -f "${BENCH_PATH}/sites/common_site_config.json" ]; then
	BENCH_DIR="${BENCH_PATH}"
else
	yellow "Where is your ERPNext bench folder? (contains sites/ and apps/)"
	read -r -p "Bench path: " BENCH_DIR
	BENCH_DIR="${BENCH_DIR/#\~/$HOME}"
fi

if [ ! -f "${BENCH_DIR}/sites/common_site_config.json" ]; then
	red "Could not find a valid bench at: ${BENCH_DIR}"
	exit 1
fi

cd "${BENCH_DIR}"
green "Using bench: ${BENCH_DIR}"

# Site name
DEFAULT_SITE=""
if [ -f "sites/currentsite.txt" ]; then
	DEFAULT_SITE="$(cat sites/currentsite.txt)"
fi
read -r -p "Site name to install on [${DEFAULT_SITE}]: " SITE
SITE="${SITE:-$DEFAULT_SITE}"
if [ -z "${SITE}" ]; then
	red "Site name is required."
	exit 1
fi

if [ ! -d "${APP_SOURCE}" ]; then
	red "App folder not found: ${APP_SOURCE}"
	exit 1
fi

bold ""
bold "Installing Total VFD on site: ${SITE}"
echo "This may take a few minutes..."
echo ""

# Link or copy app into apps/
if [ ! -d "apps/${APP_NAME}" ]; then
	ln -sf "${APP_SOURCE}" "apps/${APP_NAME}" 2>/dev/null || cp -R "${APP_SOURCE}" "apps/${APP_NAME}"
	green "App added to bench."
else
	yellow "App already exists in apps/${APP_NAME} — updating link."
	ln -sf "${APP_SOURCE}" "apps/${APP_NAME}" 2>/dev/null || true
fi

bench pip install -q requests "qrcode[pil]" Pillow bcrypt 2>/dev/null || bench pip install requests "qrcode[pil]" Pillow bcrypt

if ! bench --site "${SITE}" list-apps 2>/dev/null | grep -q "^erpnext$"; then
	red "ERPNext must be installed on this site first."
	exit 1
fi

if bench --site "${SITE}" list-apps 2>/dev/null | grep -q "^${APP_NAME}$"; then
	yellow "Total VFD is already installed — running update (migrate + build)."
else
	bench --site "${SITE}" install-app "${APP_NAME}"
fi

bench --site "${SITE}" migrate
bench build --app "${APP_NAME}"
bench restart
bench --site "${SITE}" enable-scheduler 2>/dev/null || true

echo ""
green "=========================================="
green "  Installation finished successfully!"
green "=========================================="
echo ""
bold "Next steps:"
echo "  See SETUP.md in this folder (section A for users, B for IT, C for go-live)."
echo "  In ERPNext: Total VFD → Getting Started"
echo ""
bold "Site URL (typical):"
echo "  http://${SITE}"
echo ""
