up:
	docker compose up --build

down:
	docker compose down

web-dev:
	npm --workspace apps/web run dev

api-dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
