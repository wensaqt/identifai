.PHONY: lint test generate up down logs clean

lint:
	docker compose run --rm --build test ruff check .

test:
	docker compose run --rm --build test

generate:
	docker compose run --rm --build dataset

generate-noisy:
	docker compose run --rm --build dataset --noise medium

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

clean:
	rm -rf dataset/output
	docker compose down --rmi local -v
