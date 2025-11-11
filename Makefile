.PHONY: dev lint test

dev:
@test -f .env || (echo "[info] .env 파일이 없어 .env.example을 복사합니다" && cp .env.example .env)
docker compose up --build

lint:
@echo "TODO: lint 파이프라인 구성"

test:
pytest -q
