PYTHON_CONFIG ?= python3-config
PY_CFLAGS := $(shell $(PYTHON_CONFIG) --cflags)
PY_LDFLAGS := $(shell $(PYTHON_CONFIG) --embed --ldflags 2>/dev/null)
ifeq ($(strip $(PY_LDFLAGS)),)
PY_LDFLAGS := $(shell $(PYTHON_CONFIG) --ldflags)
endif

CC ?= gcc
CFLAGS ?= -O2 -Wall -Wextra -pedantic
TARGET ?= scout_frontend

.PHONY: all clean

all: $(TARGET)

$(TARGET): frontend.c
	$(CC) $(CFLAGS) $(PY_CFLAGS) $< -o $@ $(LDFLAGS) $(PY_LDFLAGS)

clean:
	rm -f $(TARGET)
