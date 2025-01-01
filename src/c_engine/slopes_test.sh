#!/usr/bin/env bash
# Build and run the slopes.c self-test
set -e
gcc -DTEST -o /tmp/test_slopes src/c_engine/slopes.c
/tmp/test_slopes && echo "PASS: slopes.c self-test" || echo "FAIL: slopes.c self-test"
