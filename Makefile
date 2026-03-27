.PHONY: help up down build logs shell migrate makemigrations collectstatic createsuperuser restart status

help:
	@echo "Usage: make [command]"
	@echo ""
	@echo "Commands:"
	@echo "  up              - Start all services (detached)"
	@echo "  down            - Stop all services"
	@echo "  build           - Rebuild Docker images (no cache)"
	@echo "  logs            - Follow logs from all services"
	@echo "  shell           - Open Django shell inside container"
	@echo "  migrate         - Run database migrations"
	@echo "  makemigrations  - Create new migration files"
	@echo "  collectstatic   - Collect static files"
	@echo "  createsuperuser - Create Django admin superuser"
	@echo "  restart         - Restart all services"
	@echo "  status          - Show service status"

up:
	docker-compose up -d

down:
	docker-compose down

build:
	docker-compose build --no-cache

logs:
	docker-compose logs -f

shell:
	docker-compose exec django sh -c "cd src && python manage.py shell"

migrate:
	docker-compose exec django sh -c "cd src && python manage.py migrate"

makemigrations:
	docker-compose exec django sh -c "cd src && python manage.py makemigrations"

collectstatic:
	docker-compose exec django sh -c "cd src && python manage.py collectstatic --noinput"

createsuperuser:
	docker-compose exec django sh -c "cd src && python manage.py createsuperuser"

restart:
	docker-compose restart

status:
	docker-compose ps
