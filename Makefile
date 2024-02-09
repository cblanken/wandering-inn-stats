.PHONY: runserver
runserver:
	poetry run python manage.py runserver 9999

.PHONY: runserver-debug
runserver-debug:
	PYTHONBREAKPOINT=ipdb.set_trace poetry run python manage.py runserver 9999

.PHONY: build-chapters
build-chapters:
	poetry run python manage.py build --skip-wiki-all --skip-colors --skip-text-refs ./data

.PHONY: build-wiki
build-wiki:
	poetry run python manage.py build --skip-colors --skip-text-refs ./data

.PHONY: makemigrations
makemigrations:
	poetry run python manage.py makemigrations

.PHONY: migrate
migrate:
	poetry run python manage.py migrate stats

.PHONY: tailwind
tailwind:
	poetry run python manage.py tailwind start

.PHONY: generate-chart-thumbs
generate-chart-thumbs:
	poetry run python manage.py generate_chart_thumbnails

.PHONY: serve-static-files
serve-static-files:
	python -m http.server 8080 -d /tmp/twi-stats/

.PHONY: deploy
deploy:
	poetry run python manage.py collectstatic && \
	poetry run python -m gunicorn innverse.asgi:application -k uvicorn.workers.UvicornWorker
