# se_labs_prometheus/orders-api/app/metrics.py
from prometheus_client import Counter, Histogram, Gauge, Info
import time

# HTTP метрики
request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5)
)

active_requests = Gauge(
    'http_requests_active',
    'Active HTTP requests'
)

# Бизнес-метрики
order_total = Counter(
    'orders_total',
    'Total orders',
    ['status']
)

error_rate_gauge = Gauge(
    'chaos_error_rate',
    'Current chaos error rate'
)

# Системные метрики
db_connections = Gauge(
    'database_connections_active',
    'Active database connections'
)

cache_hits = Counter(
    'cache_hits_total',
    'Total cache hits'
)

cache_total = Counter(
    'cache_requests_total',
    'Total cache requests'
)

# Дополнительные бизнес-метрики
business_metrics = {
    'revenue': Counter('order_revenue_total', 'Total revenue'),
    'orders_per_customer': Counter(
        'orders_per_customer_total',
        'Orders per customer',
        ['customer_id']
    ),
    'completed_orders': Counter('orders_completed_total', 'Completed orders'),
    'cancelled_orders': Counter('orders_cancelled_total', 'Cancelled orders'),
}

# Service info
service_info = Info('service_build', 'Service build information')
service_info.info({
    'version': '1.0.0',
    'build_date': str(time.time()),
    'environment': 'development'
})