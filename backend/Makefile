.PHONY: build-IngestFunction build-AskFunction

build-IngestFunction:
	python -m pip install -r requirements.txt -t "$(ARTIFACTS_DIR)"
	cp -r lambdas "$(ARTIFACTS_DIR)/lambdas"
	cp -r shared "$(ARTIFACTS_DIR)/shared"

build-AskFunction:
	python -m pip install -r requirements.txt -t "$(ARTIFACTS_DIR)"
	cp -r lambdas "$(ARTIFACTS_DIR)/lambdas"
	cp -r shared "$(ARTIFACTS_DIR)/shared"

