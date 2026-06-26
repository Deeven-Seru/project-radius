CC     = gcc
CFLAGS = -O3 -Wall -Wextra -std=c99 -fPIC
SRC    = slopes.c mvm_reconstructor.c
OUT    = ../../build/c_engine.so

# Detect architecture to enable AVX2 only on x86_64
UNAME_M := $(shell uname -m)
ifeq ($(UNAME_M),x86_64)
	CFLAGS += -mavx2 -mfma
endif

.PHONY: all clean debug test

all:
	@mkdir -p ../../build
	$(CC) $(CFLAGS) -shared -o $(OUT) $(SRC)
	@echo "Built: $(OUT)"

debug:
	$(CC) -g -fsanitize=address -fno-omit-frame-pointer -fPIC -shared -o ../../build/c_engine_debug.so $(SRC)

test:
	gcc -DTEST -o /tmp/test_slopes slopes.c && /tmp/test_slopes
	gcc -DTEST -o /tmp/test_mvm mvm_reconstructor.c && /tmp/test_mvm
	@echo "All C-Engine self-tests PASSED"

clean:
	rm -f $(OUT)
