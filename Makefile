tests: test

build:
	docker build -t tf2-express-image .

run:
	docker-compose up -d --build mongodb tf2-express

stop:
	docker-compose down

gui:
	docker exec -it tf2-express bash -c "python3 panel.py"

test:
	docker-compose run --rm tf2-express pytest

freeze:
	docker-compose run --rm lock-generator
