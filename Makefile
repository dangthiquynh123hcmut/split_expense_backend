.PHONY: install start migrate

install-dev:
	sudo chmod +x scripts/install.sh && ./scripts/install.sh dev

start-dev:
	ENV=dev source venv/bin/activate && python src/manage.py runserver 0.0.0.0:8000

migrate-dev:
	ENV=dev source venv/bin/activate && python src/manage.py makemigrations && python src/manage.py migrate

start-prod:
	ENV=prod source venv/bin/activate && python src/manage.py runserver 0.0.0.0:8000

install-prod:
	sudo chmod +x scripts/install.sh && ./scripts/install.sh prod

migrate-prod:
	ENV=prod source venv/bin/activate && python src/manage.py makemigrations && python src/manage.py migrate

create-superuser-dev:
	ENV=dev source venv/bin/activate && python src/manage.py createsuperuser

load-initial-data-dev:
	chmod +x ./scripts/load_initial.sh && ./scripts/load_initial.sh dev

load-initial-data-prod:
	chmod +x ./scripts/load_initial.sh && ./scripts/load_initial.sh prod
