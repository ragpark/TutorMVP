# Reads .env if present. Variables: MAP_BASE_URL, ANTHROPIC_API_KEY, TUTOR_SECRET, MODEL, TUTOR_PUBLIC_URL.
-include .env
export

PY ?= .venv/bin/python
PORT ?= 8000

.PHONY: install run test register ping

.venv:
	python3.12 -m venv .venv

install: .venv
	$(PY) -m pip install -r requirements-dev.txt

run:
	$(PY) -m uvicorn app.main:app --reload --port $(PORT)

test:
	$(PY) -m pytest -q

register:
	$(PY) -m scripts.register

# Ask the map to send one trial call to a registered tutor:
#   make ping TUTOR_ID=tutor:abcd1234
ping:
	curl -sS -X POST "$(MAP_BASE_URL)/api/tutors/$(TUTOR_ID)/ping"
