CONTAINER = "doxmr"
IMAGE = "doxmr"

.PHONY: clean build run exec

all: clean build run

clean:
	-docker rm -f $(CONTAINER)

build:
	docker build . -t $(IMAGE)

run:
	docker run --rm -it --name $(CONTAINER) \
		--dns 1.1.1.1 \
		-v $(shell pwd):/app \
		$(IMAGE)

exec:
	docker exec -it $(CONTAINER) \
		sh
