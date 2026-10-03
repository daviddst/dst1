.PHONY: validate diagnose logs deploy-agent deploy-web

diagnose:
	./scripts/deploy/diagnose.sh

logs:
	@test -n "$(SERVICE)" || (echo "Usage: make logs SERVICE=dst1-agent" && exit 1)
	./scripts/deploy/diagnose.sh "$(SERVICE)"

deploy-agent:
	./scripts/deploy/deploy.sh agent

deploy-web:
	./scripts/deploy/deploy.sh web
