# WoniuNote overlay port (iteration 20).
#
# This is a verbatim copy of the vcpkg baseline port (e7b524242c8a5d718a7afa26794c3c19bb8b0c71,
# drogon 1.9.11) plus patch 0006, which makes cmake_modules/FindMySQL.cmake prefer the
# vcpkg-provided MariaDB Connector/C (unofficial::libmariadb) over any system MySQL client.
#
# Why: Drogon's MySQL ORM uses the client non-blocking API (MYSQL_OPT_NONBLOCK,
# mysql_real_connect_start, mysql_get_socket, MYSQL_WAIT_*). Oracle's MySQL 8.0 client
# removed that API, so on machines that ship MySQL 8.0 dev headers (e.g. GitHub's
# ubuntu-latest runners, whose /usr/include/mysql was picked up by the hardcoded PATHS in
# FindMySQL.cmake) drogon 1.9.11 fails to compile. Upstream drogon 1.9.12/1.9.13 still
# prefer find_package(MySQL), so no upstream fix is available; the overlay keeps the
# selection deterministic in every environment.
#
# Maintenance: when the vcpkg baseline is updated, re-copy the upstream port directory and
# re-apply patch 0006 — see ../README.md for the full procedure and the exit condition.
vcpkg_from_github(
    OUT_SOURCE_PATH SOURCE_PATH
    REPO an-tao/drogon
    REF "v${VERSION}"
    SHA512 ce61c65281bde0246e96c3558cf635241adbcab514d6a71e8267201340f577af26b1cbc69fa48652d655971122a66c70db75d1a4c034384ba0716fccf7ad9584
    HEAD_REF master
    PATCHES
         0001-vcpkg.patch
         0002-drogon-config.patch
         0003-deps-redis.patch
         0004-drogon-ctl.patch
         0005-drogon-cross-compile.patch
         0006-prefer-vcpkg-libmariadb.patch
)

set(DROGON_CTL_TOOL "")
if(VCPKG_CROSSCOMPILING)
    set(DROGON_CTL_TOOL "${CURRENT_HOST_INSTALLED_DIR}/tools/drogon/drogon_ctl${VCPKG_HOST_EXECUTABLE_SUFFIX}")
endif()

vcpkg_check_features(
    OUT_FEATURE_OPTIONS FEATURE_OPTIONS
    FEATURES
        ctl      BUILD_CTL
        mysql    BUILD_MYSQL
        orm      BUILD_ORM
        postgres BUILD_POSTGRESQL
        postgres LIBPQ_BATCH_MODE
        redis    BUILD_REDIS
        sqlite3  BUILD_SQLITE
        yaml     BUILD_YAML_CONFIG
)

string(COMPARE EQUAL "${VCPKG_LIBRARY_LINKAGE}" "dynamic" BUILD_DROGON_SHARED)

vcpkg_cmake_configure(
    SOURCE_PATH "${SOURCE_PATH}"
    DISABLE_PARALLEL_CONFIGURE
    OPTIONS
        -DBUILD_SHARED_LIBS=${BUILD_DROGON_SHARED}
        -DBUILD_EXAMPLES=OFF
        -DCMAKE_DISABLE_FIND_PACKAGE_Boost=ON
        -DUSE_SUBMODULE=OFF
        "-DDROGON_CTL_TOOL=${DROGON_CTL_TOOL}"
        ${FEATURE_OPTIONS}
    MAYBE_UNUSED_VARIABLES
        CMAKE_DISABLE_FIND_PACKAGE_Boost
)

vcpkg_cmake_install(ADD_BIN_TO_PATH)

# Fix CMake files
vcpkg_cmake_config_fixup(CONFIG_PATH lib/cmake/Drogon)

vcpkg_fixup_pkgconfig()

# Copy drogon_ctl
if("ctl" IN_LIST FEATURES)
    vcpkg_copy_tools(TOOL_NAMES drogon_ctl AUTO_CLEAN)
endif()

# Remove includes in debug
file(REMOVE_RECURSE "${CURRENT_PACKAGES_DIR}/debug/include")
file(REMOVE_RECURSE "${CURRENT_PACKAGES_DIR}/debug/share")
if(VCPKG_LIBRARY_LINKAGE STREQUAL "static")
    file(REMOVE_RECURSE "${CURRENT_PACKAGES_DIR}/bin" "${CURRENT_PACKAGES_DIR}/debug/bin")
endif()

file(INSTALL "${CMAKE_CURRENT_LIST_DIR}/usage" DESTINATION "${CURRENT_PACKAGES_DIR}/share/${PORT}")
file(INSTALL "${SOURCE_PATH}/LICENSE" DESTINATION "${CURRENT_PACKAGES_DIR}/share/${PORT}" RENAME copyright)

# Copy pdb files
vcpkg_copy_pdbs()
