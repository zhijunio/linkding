#!/usr/bin/env bash

uv run python -m coverage erase
uv run python -m coverage run manage.py test
uv run python -m coverage report --sort=cover
