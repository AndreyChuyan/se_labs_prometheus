import random
import asyncio
from typing import Optional

class ChaosEngine:
    """Chaos Engineering для тестирования"""
    
    def __init__(self):
        self.latency_ms = 0
        self.error_rate = 0.0
        self.memory_leak = []
    
    def set_latency(self, seconds: float):
        """Установить дополнительную задержку"""
        self.latency_ms = seconds
    
    def set_error_rate(self, rate: float):
        """Установить вероятность ошибки (0.0 - 1.0)"""
        self.error_rate = min(max(rate, 0.0), 1.0)
    
    async def apply_latency(self):
        """Применить настроенную задержку"""
        if self.latency_ms > 0:
            await asyncio.sleep(self.latency_ms)
    
    def should_fail(self) -> bool:
        """Определить, должен ли запрос завершиться ошибкой"""
        return random.random() < self.error_rate
    
    def create_memory_leak(self, size_mb: int = 10):
        """Создать утечку памяти"""
        # Создаём большой объект и сохраняем ссылку
        leak = bytearray(size_mb * 1024 * 1024)
        self.memory_leak.append(leak)
    
    def reset(self):
        """Сбросить все настройки"""
        self.latency_ms = 0
        self.error_rate = 0.0
        self.memory_leak.clear()