"""
Self-Healing Capabilities for AOB Platform
Implements circuit breakers, auto-recovery, health checks, and failure detection
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from dataclasses import dataclass
from contextlib import asynccontextmanager
import functools

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service is back

@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    success_threshold: int = 3
    timeout: float = 30.0

class CircuitBreaker:
    """Circuit breaker implementation for service resilience"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.last_success_time = 0
        
    def can_execute(self) -> bool:
        """Check if request can be executed"""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.config.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            return True
        
        return False
    
    def record_success(self):
        """Record successful execution"""
        self.last_success_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info(f"Circuit breaker {self.name} closed after recovery")
        
        elif self.state == CircuitState.CLOSED:
            self.failure_count = max(0, self.failure_count - 1)
    
    def record_failure(self):
        """Record failed execution"""
        self.last_failure_time = time.time()
        self.failure_count += 1
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker {self.name} opened after failed recovery")
        
        elif self.state == CircuitState.CLOSED and self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker {self.name} opened due to failures")

class HealthChecker:
    """Health check implementation for services"""
    
    def __init__(self, name: str, check_func: Callable, interval: float = 30.0):
        self.name = name
        self.check_func = check_func
        self.interval = interval
        self.is_healthy = True
        self.last_check = 0
        self.last_error = None
        self._task = None
    
    async def start(self):
        """Start health checking"""
        if self._task is None:
            self._task = asyncio.create_task(self._health_check_loop())
    
    async def stop(self):
        """Stop health checking"""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
    
    async def _health_check_loop(self):
        """Health check loop"""
        while True:
            try:
                await self.check_func()
                self.is_healthy = True
                self.last_error = None
                self.last_check = time.time()
            except Exception as e:
                self.is_healthy = False
                self.last_error = str(e)
                self.last_check = time.time()
                logger.error(f"Health check failed for {self.name}: {e}")
            
            await asyncio.sleep(self.interval)
    
    async def check_now(self) -> bool:
        """Perform immediate health check"""
        try:
            await self.check_func()
            self.is_healthy = True
            self.last_error = None
            self.last_check = time.time()
            return True
        except Exception as e:
            self.is_healthy = False
            self.last_error = str(e)
            self.last_check = time.time()
            return False

class RetryPolicy:
    """Retry policy with exponential backoff"""
    
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0, max_delay: float = 60.0, jitter: bool = True):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt"""
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        
        if self.jitter:
            # Add jitter to prevent thundering herd
            import random
            delay *= (0.5 + random.random() * 0.5)
        
        return delay

class SelfHealingManager:
    """Central manager for self-healing capabilities"""
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.health_checkers: Dict[str, HealthChecker] = {}
        self.retry_policies: Dict[str, RetryPolicy] = {}
        self.recovery_handlers: Dict[str, Callable] = {}
    
    def add_circuit_breaker(self, name: str, config: CircuitBreakerConfig):
        """Add a circuit breaker"""
        self.circuit_breakers[name] = CircuitBreaker(name, config)
    
    def add_health_checker(self, name: str, check_func: Callable, interval: float = 30.0):
        """Add a health checker"""
        self.health_checkers[name] = HealthChecker(name, check_func, interval)
    
    def add_retry_policy(self, name: str, policy: RetryPolicy):
        """Add a retry policy"""
        self.retry_policies[name] = policy
    
    def add_recovery_handler(self, name: str, handler: Callable):
        """Add a recovery handler"""
        self.recovery_handlers[name] = handler
    
    async def start_all(self):
        """Start all health checkers"""
        for checker in self.health_checkers.values():
            await checker.start()
    
    async def stop_all(self):
        """Stop all health checkers"""
        for checker in self.health_checkers.values():
            await checker.stop()
    
    def get_circuit_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name"""
        return self.circuit_breakers.get(name)
    
    def get_health_checker(self, name: str) -> Optional[HealthChecker]:
        """Get health checker by name"""
        return self.health_checkers.get(name)
    
    def get_retry_policy(self, name: str) -> Optional[RetryPolicy]:
        """Get retry policy by name"""
        return self.retry_policies.get(name)
    
    def get_recovery_handler(self, name: str) -> Optional[Callable]:
        """Get recovery handler by name"""
        return self.recovery_handlers.get(name)
    
    async def execute_with_resilience(self, name: str, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker and retry logic"""
        
        # Get circuit breaker
        circuit_breaker = self.get_circuit_breaker(name)
        if circuit_breaker and not circuit_breaker.can_execute():
            raise Exception(f"Circuit breaker {name} is open")
        
        # Get retry policy
        retry_policy = self.get_retry_policy(name)
        if not retry_policy:
            retry_policy = RetryPolicy()
        
        last_exception = None
        
        for attempt in range(retry_policy.max_attempts):
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # Record success
                if circuit_breaker:
                    circuit_breaker.record_success()
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Record failure
                if circuit_breaker:
                    circuit_breaker.record_failure()
                
                # Check if we should retry
                if attempt < retry_policy.max_attempts - 1:
                    delay = retry_policy.get_delay(attempt)
                    logger.warning(f"Attempt {attempt + 1} failed for {name}, retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All attempts failed for {name}: {e}")
        
        # All retries failed, trigger recovery if available
        recovery_handler = self.get_recovery_handler(name)
        if recovery_handler:
            try:
                logger.info(f"Triggering recovery for {name}")
                if asyncio.iscoroutinefunction(recovery_handler):
                    await recovery_handler()
                else:
                    recovery_handler()
            except Exception as e:
                logger.error(f"Recovery failed for {name}: {e}")
        
        raise last_exception

# Global self-healing manager
self_healing_manager = SelfHealingManager()

# Decorators for easy use
def circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None):
    """Decorator for circuit breaker"""
    if config is None:
        config = CircuitBreakerConfig()
    
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await self_healing_manager.execute_with_resilience(name, func, *args, **kwargs)
        return wrapper
    return decorator

def retry_with_policy(name: str, policy: Optional[RetryPolicy] = None):
    """Decorator for retry policy"""
    if policy is None:
        policy = RetryPolicy()
    
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await self_healing_manager.execute_with_resilience(name, func, *args, **kwargs)
        return wrapper
    return decorator

def health_check(name: str, interval: float = 30.0):
    """Decorator for health check"""
    def decorator(func):
        self_healing_manager.add_health_checker(name, func, interval)
        return func
    return decorator

# Common health check functions
async def check_database_health(connection_string: str):
    """Check database health"""
    import asyncpg
    try:
        conn = await asyncpg.connect(connection_string)
        await conn.execute("SELECT 1")
        await conn.close()
    except Exception as e:
        raise Exception(f"Database health check failed: {e}")

async def check_redis_health(redis_url: str):
    """Check Redis health"""
    import redis.asyncio as redis
    try:
        r = redis.from_url(redis_url)
        await r.ping()
        await r.close()
    except Exception as e:
        raise Exception(f"Redis health check failed: {e}")

async def check_kafka_health(bootstrap_servers: str):
    """Check Kafka health"""
    from kafka import KafkaProducer
    try:
        producer = KafkaProducer(bootstrap_servers=bootstrap_servers)
        producer.close()
    except Exception as e:
        raise Exception(f"Kafka health check failed: {e}")

async def check_http_service_health(url: str):
    """Check HTTP service health"""
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5.0)
            response.raise_for_status()
    except Exception as e:
        raise Exception(f"HTTP service health check failed: {e}")

# Recovery handlers
async def restart_service_handler(service_name: str):
    """Generic service restart handler"""
    logger.info(f"Restarting service {service_name}")
    # Implementation would depend on deployment method
    # For Docker: docker restart service_name
    # For Kubernetes: kubectl rollout restart deployment/service_name
    pass

async def clear_cache_handler(cache_name: str):
    """Clear cache handler"""
    logger.info(f"Clearing cache {cache_name}")
    # Implementation would clear relevant caches
    pass

async def reset_connections_handler(service_name: str):
    """Reset connections handler"""
    logger.info(f"Resetting connections for {service_name}")
    # Implementation would reset connection pools
    pass

# Initialize self-healing for common services
def init_self_healing():
    """Initialize self-healing for common services"""
    
    # Add circuit breakers for common services
    self_healing_manager.add_circuit_breaker("database", CircuitBreakerConfig())
    self_healing_manager.add_circuit_breaker("redis", CircuitBreakerConfig())
    self_healing_manager.add_circuit_breaker("kafka", CircuitBreakerConfig())
    self_healing_manager.add_circuit_breaker("model_gateway", CircuitBreakerConfig())
    self_healing_manager.add_circuit_breaker("tool_gateway", CircuitBreakerConfig())
    
    # Add retry policies
    self_healing_manager.add_retry_policy("database", RetryPolicy(max_attempts=3, base_delay=1.0))
    self_healing_manager.add_retry_policy("redis", RetryPolicy(max_attempts=3, base_delay=0.5))
    self_healing_manager.add_retry_policy("kafka", RetryPolicy(max_attempts=5, base_delay=2.0))
    
    # Add recovery handlers
    self_healing_manager.add_recovery_handler("database", lambda: restart_service_handler("postgres"))
    self_healing_manager.add_recovery_handler("redis", lambda: restart_service_handler("redis"))
    self_healing_manager.add_recovery_handler("kafka", lambda: restart_service_handler("kafka"))
    
    logger.info("Self-healing capabilities initialized")

# Context manager for resilient execution
@asynccontextmanager
async def resilient_execution(name: str):
    """Context manager for resilient execution"""
    try:
        yield
    except Exception as e:
        logger.error(f"Resilient execution failed for {name}: {e}")
        # Trigger recovery if available
        recovery_handler = self_healing_manager.get_recovery_handler(name)
        if recovery_handler:
            try:
                if asyncio.iscoroutinefunction(recovery_handler):
                    await recovery_handler()
                else:
                    recovery_handler()
            except Exception as recovery_error:
                logger.error(f"Recovery failed for {name}: {recovery_error}")
        raise
