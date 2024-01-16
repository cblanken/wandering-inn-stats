.PHONY: runserver
runserver:
	poetry run python manage.py runserver 9999

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

.PHONY: serve-static-files
serve-static-files:
	python -m http.server 8080 -d /tmp/twi-stats/

.PHONY: run-dev
run-dev:
	$(MAKE) tailwind &
	$(MAKE) serve-static-files &
	$(MAKE) runserver | tee run.log

.PHONY: kill-dev
kill-dev:
	pkill -9 -f "python -m http.server 8080 -d /tmp/twi-stats"
	pkill -9 -f "python manage.py runserver 9999"
