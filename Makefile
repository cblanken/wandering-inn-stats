.PHONY: install
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
