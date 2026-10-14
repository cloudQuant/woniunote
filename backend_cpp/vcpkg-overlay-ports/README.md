# vcpkg overlay ports (WoniuNote)

This directory is wired into the build by `backend_cpp/vcpkg-configuration.json`
(`"overlay-ports": ["./vcpkg-overlay-ports"]`). vcpkg prefers a port found here
over the one in the pinned baseline.

## `drogon` — why this overlay exists

Drogon's MySQL ORM uses the MySQL client **non-blocking API**
(`MYSQL_OPT_NONBLOCK`, `mysql_real_connect_start()`, `mysql_get_socket()`,
`MYSQL_WAIT_*`). Oracle's MySQL 8.0 client removed that API; MariaDB
Connector/C still provides it.

Upstream drogon 1.9.11's `cmake_modules/FindMySQL.cmake` searches hardcoded
system paths *before* the vcpkg-provided client, so on a machine that ships
MySQL 8.0 development headers (GitHub's `ubuntu-latest` runner images do, via
`/usr/include/mysql`) drogon selected the wrong client and failed to compile:

```
MysqlConnection.cc:62:36: error: 'MYSQL_OPT_NONBLOCK' was not declared in this scope
```

This was the first real failure of the `backend-cpp` CI job at the iteration-20
baseline — not a CMake version problem. Upstream drogon 1.9.12/1.9.13 still
prefer `find_package(MySQL)`, so no released fix exists; the overlay pins the
selection deterministically in every environment.

`0006-prefer-vcpkg-libmariadb.patch` makes `FindMySQL.cmake` use
`find_package(unofficial-libmariadb CONFIG)` and, when it resolves, sets
`MYSQL_INCLUDE_DIRS` / `MYSQL_LIBRARIES` from that target before the system
search runs. The rest of the port directory is a **verbatim copy** of the
baseline port.

## Maintenance: when the vcpkg baseline is updated

1. Check whether the new drogon port still needs the patch. If upstream now
   selects the vcpkg client (or another fix landed), **delete this overlay
   directory** rather than carrying it forward — an overlay that no longer
   changes anything is pure maintenance debt.
2. If it is still needed: copy the new baseline port directory
   (`ports/drogon/` at the new baseline commit) over this one, then re-apply
   `0006-prefer-vcpkg-libmariadb.patch`. Keep the header comment and the
   `PATCHES` entry accurate.
3. Update `builtin-baseline` in `backend_cpp/vcpkg.json` and the
   `VCPKG_BASELINE` env value in `.github/workflows/cpp-vue-ci.yml` together.
   The CI cache key hashes `backend_cpp/vcpkg-overlay-ports/**`, so a changed
   patch correctly invalidates the cached build.
4. Rebuild in a clean build directory (the patch changes drogon's ABI hash) and
   re-run the full backend gate: `ctest --output-on-failure --no-tests=error`
   plus the HTTP integration suite.

## Verifying the patch was applied

```bash
# vcpkg logs "installing overlay port from here" while building drogon, and the
# patched file is visible in the vcpkg build tree:
grep -n "unofficial-libmariadb" ~/vcpkg/buildtrees/drogon/src/*/cmake_modules/FindMySQL.cmake
```

A simpler end-to-end check: `bash backend_cpp/build.sh` (or the CI
`backend-cpp` job) must configure and compile drogon without the
`MYSQL_OPT_NONBLOCK` error.
