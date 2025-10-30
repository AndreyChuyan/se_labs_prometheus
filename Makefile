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
	cd monitoring-stack && docker-compose up -d --build
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
	@curl -s http://localhost:8080/health | jq '. + {uptime: (.uptime | strftime("%Y-%m-%d %H:%M:%S"))}'
	@echo "\nTesting Prometheus targets..."
	@curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, instance: .labels.instance, health: .health, lastError: .lastError}'
	
## ============================================================================
## 🧪 Chaos Engineering
## ============================================================================

chaos-latency: ## 🐌 Add 500ms latency to requests
	@echo "$(YELLOW)🐌 Adding 500ms latency...$(NC)"
	@curl -sf -X POST "http://localhost:8080/chaos/latency?ms=500" || echo "$(RED)Failed$(NC)"
	@echo "$(GREEN)✅ Latency chaos enabled$(NC)"
	@echo "$(YELLOW)💡 Watch P95 latency in Grafana$(NC)"

chaos-latency-search: ## 🔍 Slow down /search endpoint
	@curl -sf -X POST "http://localhost:8080/chaos/latency-search?ms=500" || echo "$(RED)Failed$(NC)"
	@echo "✅ Search latency: 500ms"

chaos-errors: ## 💥 Set 30% error rate
	@echo "$(YELLOW)💥 Setting 30% error rate...$(NC)"
	@curl -sf -X POST "http://localhost:8080/chaos/errors?rate=0.3" || echo "$(RED)Failed$(NC)"
	@echo "$(GREEN)✅ Error chaos enabled$(NC)"
	@echo "$(YELLOW)💡 Watch error rate in Grafana$(NC)"

chaos-reset: ## ♻️  Reset all chaos settings
	@echo "$(BLUE)♻️  Resetting chaos...$(NC)"
	@curl -sf -X POST "http://localhost:8080/chaos/reset" || echo "$(RED)Failed$(NC)"
	@echo "$(GREEN)✅ Chaos reset$(NC)"

chaos-status: ## 📊 Show current chaos status
	@echo "$(CYAN)📊 Current Chaos Status:$(NC)"
	@curl -s http://localhost:8080/chaos/status | jq '.' || echo "$(RED)❌ Cannot fetch chaos status$(NC)"

## ============================================================================
## 🔧 Load Testing
## ============================================================================

# - Всплеск (load-test),
# - Постоянная нагрузка (sustained),
# - Тест конкретных эндпоинтов (search),
# - Смешанный поток запросов с выводом для отладки (mixed).

load-test: ## 🚀 Generate short load burst (100 requests)
	@echo "🚀 Generating load (100 requests)..."
	@bash -c 'for i in {1..100}; do \
		curl -s http://localhost:8080/orders?limit=10 > /dev/null & \
	done; wait'
	@echo "✅ Load test completed"

load-test-sustained: ## 🔄 Generate sustained load (10 req/s for 60s)
	@echo "🔄 Generating sustained load (10 req/s for 60 seconds)..."
	@echo "⚠️  Press Ctrl+C to stop"
	@bash -c 'for i in {1..300}; do \
		curl -s http://localhost:8080/orders > /dev/null & \
		sleep 0.2; \
	done; wait'
	@echo "✅ Sustained load test completed"

load-test-search: ## 🔍 Test search endpoint
	@echo "🔍 Testing /search endpoint..."
	@bash -c 'for i in {1..50}; do \
		curl -s "http://localhost:8080/search?q=order$$i" > /dev/null & \
	done; wait'
	@echo "✅ Search load test completed"

load-test-mixed: ## 🔍 Mixed load with debug output
	@echo "🎲 Generating weighted mixed load (DEBUG)..."
	@bash -c 'for i in {1..20}; do \
		rand=$$((RANDOM % 100)); \
		if [ $$rand -lt 60 ]; then \
			echo "→ /orders (rand=$$rand)"; \
			curl -s "http://localhost:8080/orders?limit=10" > /dev/null & \
		elif [ $$rand -lt 90 ]; then \
			echo "→ /search (rand=$$rand)"; \
			curl -s "http://localhost:8080/search?q=order$$i" > /dev/null & \
		else \
			echo "→ /health (rand=$$rand)"; \
			curl -s "http://localhost:8080/health" > /dev/null & \
		fi; \
		delay=$$(awk -v min=0.05 -v max=0.5 "BEGIN{srand(); print min+rand()*(max-min)}"); \
		printf "  delay: %.3fs\n" $$delay; \
		sleep $$delay; \
	done; wait'
	@echo "✅ Debug load test completed"
	


dashboard-import: ## Import Grafana dashboard
	@echo "Importing dashboard..."
	@curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
		-H "Content-Type: application/json" \
		-d @monitoring-stack/grafana/provisioning/dashboards/orders-api.json

clean: ## Clean all data
	cd monitoring-stack && docker-compose down -v
	docker system prune -f