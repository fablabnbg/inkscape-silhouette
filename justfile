#!/usr/bin/env just --justfile

# run local test (Must have umockdev installed)
test:
	pytest -s -vv test
