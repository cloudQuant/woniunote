# WoniuNote - Quantitative Blog System

<div align="center">

[![C++](https://img.shields.io/badge/C++-17+-00599C.svg)](https://isocpp.org/)
[![Drogon](https://img.shields.io/badge/Drogon-1.9+-blue.svg)](https://github.com/drogonframework/drogon)
[![Vue](https://img.shields.io/badge/Vue-3.4+-4FC08D.svg)](https://vuejs.org/)
[![Element Plus](https://img.shields.io/badge/Element%20Plus-2.5+-409EFF.svg)](https://element-plus.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**A high-performance blog system with a separated frontend and backend, built on C++ Drogon + Vue 3 + Element Plus**

🌐 **Live demo**: [https://www.yunjinqi.top](https://www.yunjinqi.top)

[中文](README.md) | [English](#overview)

</div>

---

## Overview

WoniuNote is a blog system using a **separated frontend/backend architecture** with a
high-performance C++ backend, covering articles, user management, comments, favorites and
math training.

> Badges above name the stable product series only. Exact tool and dependency versions come
> from `frontend/package-lock.json` and `backend_cpp/vcpkg.json` — not from the badge text.

### Architecture

```
[Frontend: Vue 3 + Vite + Element Plus]
           ↓ (API calls)
[Nginx] → Reverse proxy / static file serving
           ↓ (/api/*)
[C++ Backend: Drogon framework]
           ↓
[MySQL 8.0 + Redis]
```

## 🌿 Branches and versions

| Item | Value |
|---|---|
| Active development branch | `dev_cpp` (also the current **default branch** on GitHub) |
| Historical mainline | `master` (Flask era; no active development) |
| Current release | `2.0.0` (source release: C++ Drogon backend + Vue 3 frontend) |
| Single source of truth | `project(... VERSION)` in `backend_cpp/CMakeLists.txt` |

The version must match in `backend_cpp/CMakeLists.txt`, `frontend/package.json` and
`backend_cpp/vcpkg.json`; `bash scripts/check_release_version.sh` verifies this (run by the
`repo-hygiene` CI job). The legacy `setup.py` (0.1.5), the Sphinx documentation site (1.0.0)
and the archived Python/Flask implementation are **historical** and do not describe this
release.

The `/api/...` route prefix is independent of the product release number.

## 🚀 Quick start

### Requirements

| Component | Requirement |
|---|---|
| C++ compiler | GCC 10+ / Clang 13+ / MSVC 2019+ |
| CMake | 3.20+ |
| vcpkg | pinned baseline `e7b524242c8a5d718a7afa26794c3c19bb8b0c71` (see `backend_cpp/vcpkg.json`) |
| Node.js | >= 20.19.0 (CI and deployment acceptance version: 22.13.0) |
| npm | >= 10 |
| MySQL | 8.0+ |
| Redis | 6.0+ (optional but recommended; required for rate limiting) |

Frontend dependencies are pinned by `frontend/package-lock.json`: install with `npm ci`
(never delete the lockfile or fall back to `npm install`). `npm run check:node` validates the
Node version against `engines` before installing or building.

### One-command start (recommended)

```bash
# Clone
git clone https://github.com/cloudQuant/woniunote.git
cd woniunote

# Development mode (frontend hot-reload)
bash start_app.sh dev

# Production mode (frontend built + served by Nginx)
bash start_app.sh prod

# Frontend: http://localhost:8888 (dev) | Backend API: http://localhost:5173
```

Stop and restart with `bash stop_app.sh` / `bash restart_app.sh [prod|dev]`.

### Manual start

```bash
# Backend (C++)
cd backend_cpp
./build.sh                       # wraps CMake + vcpkg
cd build && ./woniunote_backend  # listens on 5173

# Frontend (Vue 3)
cd frontend
npm run check:node               # Node >= 20.19.0
npm ci                           # lockfile-exact install
npm run dev                      # dev server on 8888
npm run build                    # production build into dist/
```

System-library builds (without vcpkg) are also supported:

```bash
mkdir build && cd build
cmake .. -DUSE_SYSTEM_LIBS=ON
cmake --build . --config Release
```

### Production deployment (Ubuntu 22.04 + HTTPS)

```bash
sudo bash scripts/setup_ubuntu.sh
```

The script installs system dependencies, MySQL 8.0, Redis, Node.js 22.x (upgrading an
existing Node that does not satisfy the frontend `engines`), vcpkg and the C++ dependencies,
then compiles the backend. It fails loudly instead of continuing when the Node version or
`npm ci` does not satisfy the requirements.

## 🧪 Tests and quality gates

```bash
# Backend C++ (BUILD_TESTING is OFF by default; turn it on explicitly)
cd backend_cpp/build
ctest --output-on-failure --no-tests=error

# Backend HTTP integration tests (needs an isolated test MySQL + Redis)
bash backend_cpp/tests/integration/run_integration.sh

# Frontend gates
cd frontend
npm run lint:ci
npm run test:coverage    # thresholds: 95% on all four metrics
npm run build
PW_BROWSERS=all npm run test:e2e   # chromium + firefox + webkit + mobile-chrome
npm run audit:ci
```

`docs/archive/legacy-flask-tests/` is an archive of the old Flask test suite; it is **not** a
quality gate for the active `dev_cpp` stack.

## 📡 API endpoints

| Module | Endpoints | Description |
|--------|-----------|-------------|
| Auth | `/api/auth/*` | Login, Register, Logout, Refresh |
| Articles | `/api/article/*` | CRUD, Search, Categories, Navigation |
| Comments | `/api/comment/*` | Comment, Reply, Vote |
| Favorites | `/api/favorite/*` | Bookmark management |
| Users | `/api/user/*` | User profile |
| Math | `/api/math/*` | Math training |
| Admin | `/api/admin/*` | Admin dashboard |
| System | `/api/health`, `/api/status` | Health and version responses |

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

⭐ If this project helps you, please give it a star!
