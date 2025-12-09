# Test Directory

This directory will contain unit tests using Drogon's testing framework.

## Structure

```
tests/
├── CMakeLists.txt
├── test_auth.cc
├── test_articles.cc
└── ...
```

## Running Tests

```bash
cd build
cmake .. -DBUILD_TESTING=ON
cmake --build .
ctest --output-on-failure
```
