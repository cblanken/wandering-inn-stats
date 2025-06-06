.PHONY: runserver
runserver:
	uv run python manage.py runserver 9999

.PHONY: runserver-debug
runserver-debug:
	PYTHONBREAKPOINT=ipdb.set_trace uv run python manage.py runserver 9999

.PHONY: build-chapters
build-chapters:
	uv run python manage.py build --skip-wiki-all --skip-colors --skip-text-refs ./data

.PHONY: build-wiki
build-wiki:
	uv run python manage.py build --skip-colors --skip-text-refs ./data

.PHONY: makemigrations
makemigrations:
	uv run python manage.py makemigrations

.PHONY: migrate
migrate:
	uv run python manage.py migrate stats

.PHONY: tailwind
tailwind:
	uv run python manage.py tailwind start

.PHONY: generate-chart-thumbs
generate-chart-thumbs:
	uv run python manage.py generate_chart_thumbnails

.PHONY: serve-static-files
serve-static-files:
	uv run python -m http.server 8080 -d /tmp/twi-stats/

.PHONY: deploy
deploy:
	sudo chown -R www-data:www-data /var/www/static && \
	uv run python -m gunicorn innverse.asgi:application -k uvicorn.workers.UvicornWorker
