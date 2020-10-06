CONTAINER = "doxmr"
IMAGE = "doxmr"

.PHONY: clean build run exec

all: clean build run

clean:
	-docker rm -f $(CONTAINER)

build:
	docker build . -t $(IMAGE)

run:
	docker run -d --name $(CONTAINER) \
		--dns 1.1.1.1 \
		--restart unless-stopped \
		$(IMAGE)

exec:
	docker exec -it $(CONTAINER) \
		sh
