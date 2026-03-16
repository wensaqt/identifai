.PHONY: install generate up down logs clean

install:
	python -m venv .venv
	.venv/bin/pip install -r dataset/requirements.txt

generate:
	.venv/bin/python -m dataset.generate

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

clean:
	rm -rf dataset/output
	docker compose down --rmi local -v
