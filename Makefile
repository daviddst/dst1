.PHONY: validate checklist status

validate:
	./scripts/validate.sh

checklist:
	./scripts/manual-copy-checklist.sh

status:
	git status --short
