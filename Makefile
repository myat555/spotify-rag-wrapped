.PHONY: up down logs synth seed combine-real seed-real status traits

up:
	docker compose up --build --scale worker=3 -d

down:
	docker compose down

logs:
	docker compose logs -f worker backend

# --- Synthetic data path (no real export needed) ---

synth:
	python3 data/generate_synthetic_history.py

seed:
	curl -s -X POST http://localhost:8000/ingest/start \
		-H "Content-Type: application/json" \
		-d '{"export_path": "/data/sample_export/endsong_0.json"}' | python3 -m json.tool

# --- Real Spotify export path ---
# Usage: make combine-real EXPORT_DIR="/path/to/Spotify Extended Streaming History"

combine-real:
	python3 data/combine_real_export.py "$(EXPORT_DIR)"

seed-real:
	curl -s -X POST http://localhost:8000/ingest/start \
		-H "Content-Type: application/json" \
		-d '{"export_path": "/data/sample_export/real_history.json"}' | python3 -m json.tool

# --- Status / results ---

status:
	@curl -s http://localhost:8000/ingest/status/$(JOB_ID) | python3 -m json.tool

traits:
	@curl -s http://localhost:8000/traits/summary | python3 -m json.tool
