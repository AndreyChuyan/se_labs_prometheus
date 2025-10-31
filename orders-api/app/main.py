# se_labs_prometheus/orders-api/app/main.py
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
import random
import time
import asyncio
from datetime import datetime
from typing import Optional
import uvicorn
import re

from .metrics import (
    request_count,
    request_duration,
    active_requests,
    order_total,
    error_rate_gauge,
    db_connections,
    cache_hits,
    cache_total,
    business_metrics
)
from .chaos import ChaosEngine
from .models import Order, OrderStatus, HealthCheck

app = FastAPI(title="Orders API", version="1.0.0")
chaos = ChaosEngine()

@app.middleware("http")
async def metrics_middleware(request, call_next):
    if request.url.path == "/metrics":
        return await call_next(request)

    # Нормализуем путь до шаблона
    path = request.url.path
    
    # Паттерны для замены динамических частей
    patterns = [
        (r'^/orders/[^/]+/status$', '/orders/{order_id}/status'),
        (r'^/orders/[^/]+$', '/orders/{order_id}'),
        (r'^/customers/[^/]+$', '/customers/{customer_id}'),
    ]
    
    endpoint = path
    for pattern, template in patterns:
        if re.match(pattern, path):
            endpoint = template
            break

    active_requests.inc()
    start = time.perf_counter()
    
    try:
        response = await call_next(request)
        dur = time.perf_counter() - start

        request_count.labels(
            method=request.method,
            endpoint=endpoint,
            status=str(response.status_code),
        ).inc()

        request_duration.labels(
            method=request.method,
            endpoint=endpoint,
        ).observe(dur)

        return response
    finally:
        active_requests.dec()

@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "service": "Orders API",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check() -> HealthCheck:
    """Health check endpoint"""
    # Симуляция проверки зависимостей
    db_status = random.choice(["healthy", "healthy", "healthy", "degraded"])
    cache_status = "healthy" if random.random() > 0.05 else "unhealthy"
    
    db_connections.set(random.randint(5, 50))
    
    return HealthCheck(
        status="healthy" if db_status == "healthy" and cache_status == "healthy" else "degraded",
        database=db_status,
        cache=cache_status,
        uptime=time.time()
    )

@app.get("/orders")
async def get_orders(
    limit: int = Query(10, le=100),
    offset: int = Query(0, ge=0),
    fail: bool = Query(False, description="Force failure for testing")
):
    """Получить список заказов"""
    # Применяем chaos engineering
    await chaos.apply_latency()
    
    if fail or chaos.should_fail():
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    # Симуляция работы с кешем
    if random.random() > 0.3:  # 70% cache hit rate
        cache_hits.inc()
    cache_total.inc()
    
    # Симуляция обработки
    await asyncio.sleep(random.uniform(0.01, 0.1))
    
    orders = [
        {
            "id": f"ORD-{offset + i:04d}",
            "customer_id": f"CUST-{random.randint(1, 100):03d}",
            "amount": round(random.uniform(10, 500), 2),
            "status": random.choice(["pending", "processing", "completed", "cancelled"]),
            "created_at": datetime.utcnow().isoformat()
        }
        for i in range(limit)
    ]
    
    return {
        "orders": orders,
        "total": 1000,
        "limit": limit,
        "offset": offset
    }

@app.post("/orders")
async def create_order(order: Order):
    """Создать новый заказ"""
    await chaos.apply_latency()
    
    if chaos.should_fail():
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    
    # Симуляция обработки
    processing_time = random.uniform(0.05, 0.5)
    await asyncio.sleep(processing_time)
    
    # Обновляем бизнес-метрики
    order_total.labels(status="created").inc()
    business_metrics["revenue"].inc(order.amount)
    business_metrics["orders_per_customer"].labels(
        customer_id=order.customer_id
    ).inc()
    
    return {
        "id": f"ORD-{random.randint(1000, 9999)}",
        "status": "created",
        "processing_time": processing_time,
        **order.dict()
    }

@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    """Получить заказ по ID"""
    await chaos.apply_latency()
    
    if chaos.should_fail():
        raise HTTPException(status_code=500, detail="Database error")
    
    if random.random() < 0.1:  # 10% вероятность не найти заказ
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {
        "id": order_id,
        "customer_id": f"CUST-{random.randint(1, 100):03d}",
        "amount": round(random.uniform(10, 500), 2),
        "status": random.choice(["pending", "processing", "completed"]),
        "created_at": datetime.utcnow().isoformat(),
        "items": [
            {"product_id": f"PROD-{i:03d}", "quantity": random.randint(1, 5)}
            for i in range(random.randint(1, 5))
        ]
    }

@app.put("/orders/{order_id}/status")
async def update_order_status(order_id: str, status: OrderStatus):
    """Обновить статус заказа"""
    await chaos.apply_latency()
    
    if chaos.should_fail():
        raise HTTPException(status_code=500, detail="Failed to update status")

    old_status = random.choice(["pending", "processing"])
    order_total.labels(status=f"{old_status}_to_{status.status}").inc()
    
    if status.status == "completed":
        business_metrics["completed_orders"].inc()
    elif status.status == "cancelled":
        business_metrics["cancelled_orders"].inc()
    
    return {
        "id": order_id,
        "old_status": old_status,
        "new_status": status.status,
        "updated_at": datetime.utcnow().isoformat()
    }

# Chaos Engineering endpoints
@app.post("/chaos/latency")
async def set_latency(ms: int = Query(..., ge=0, le=5000)):
    """Установить дополнительную задержку"""
    chaos.set_latency(ms / 1000)
    return {"message": f"Latency set to {ms}ms"}

@app.post("/chaos/errors")
async def set_error_rate(rate: float = Query(..., ge=0, le=1)):
    """Установить процент ошибок"""
    chaos.set_error_rate(rate)
    error_rate_gauge.set(rate)
    return {"message": f"Error rate set to {rate*100}%"}

@app.post("/chaos/reset")
async def reset_chaos():
    """Сбросить все chaos-настройки"""
    chaos.reset()
    error_rate_gauge.set(0)
    return {"message": "Chaos settings reset"}

@app.delete("/chaos/memory-leak")
async def simulate_memory_leak(size_mb: int = Query(10, ge=1, le=1000)):
    """Симулировать утечку памяти"""
    # Создаём большой объект который не удаляется
    chaos.create_memory_leak()
    return {"message": "Memory leak started"}

@app.post("/chaos/latency-search")
async def set_search_latency(ms: int = Query(..., ge=0, le=5000)):
    """Установить задержку только для /search"""
    chaos.set_search_latency(ms / 1000)
    return {"message": f"Search latency set to {ms}ms"}

@app.get("/search")
async def search_orders(q: str = Query("", description="Search query")):
    """Поиск заказов"""
    await chaos.apply_latency_search()  # ✅
    
    if chaos.should_fail():
        raise HTTPException(status_code=500, detail="Search service unavailable")

    # Симуляция поиска
    await asyncio.sleep(random.uniform(0.05, 0.15))
    
    results = [
        {
            "id": f"ORD-{random.randint(1, 9999):04d}",
            "customer_id": f"CUST-{random.randint(1, 100):03d}",
            "amount": round(random.uniform(10, 500), 2),
            "status": random.choice(["pending", "completed"]),
            "relevance": round(random.random(), 2)
        }
        for _ in range(random.randint(5, 20))
    ]
    
    return {"query": q, "results": results, "total": len(results)}

@app.get("/chaos/status")
async def chaos_status():
    """Получить текущие настройки chaos"""
    return {
        "latency_ms": chaos.latency_ms * 1000,
        "search_latency_ms": chaos.search_latency_ms * 1000,
        "error_rate": chaos.error_rate,
        "memory_leak_size": len(chaos.memory_leak)
    }

# Metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(REGISTRY), media_type="text/plain")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)