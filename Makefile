.PHONY: help build up down logs test chaos-latency chaos-errors load-test

help: ## 📌 Show this help message
	@echo " _     _ "
	@echo "  \___/    SE_Labs_Prometheus"
	@echo " ( ^_^ )   "
	@echo " /| o |\   🐞 Dbgops"
	@echo " /|___|\   by Andrey Chuyan"
	@echo " _/  \_    https://chuyana.ru"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build all containers
	cd monitoring-stack && docker-compose build

up: ## Start all services
	cd monitoring-stack && docker-compose up -d
	@echo "✅ Services started!"
	@echo "📊 Grafana: http://localhost:3000 (admin/admin)"
	@echo "🔥 Prometheus: http://localhost:9090"
	@echo "🚨 AlertManager: http://localhost:9093"
	@echo "🎯 Orders API: http://localhost:8080"
	@echo "📈 Orders API Metrics: http://localhost:8080/metrics"

down: ## Stop all services
	cd monitoring-stack && docker-compose down

logs: ## Show logs
	cd monitoring-stack && docker-compose logs -f

test: ## Run basic tests
	@echo "Testing Orders API..."
	@curl -s http://localhost:8080/health | jq
	@echo "\nTesting Prometheus targets..."
	@curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .job, health: .health}'

chaos-latency: ## Add 500ms latency
	curl -X POST "http://localhost:8080/chaos/latency?ms=500"

chaos-errors: ## Set 30% error rate
	curl -X POST "http://localhost:8080/chaos/errors?rate=0.3"

chaos-reset: ## Reset chaos settings
	curl -X POST "http://localhost:8080/chaos/reset"

load-test: ## Generate load for testing
	@echo "Generating load..."
	@for i in {1..100}; do \
		curl -s http://localhost:8080/orders > /dev/null & \
	done
	@wait
	@echo "✅ Load test completed"

dashboard-import: ## Import Grafana dashboard
	@echo "Importing dashboard..."
	@curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
		-H "Content-Type: application/json" \
		-d @monitoring-stack/grafana/provisioning/dashboards/orders-api.json

clean: ## Clean all data
	cd monitoring-stack && docker-compose down -v
	docker system prune -f