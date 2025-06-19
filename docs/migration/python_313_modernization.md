# Python 3.13 Modernization Guide

## Overview

This guide covers the modernization of TripSage codebase to leverage Python 3.13's latest features, including improved type parameter syntax, performance enhancements, and modern patterns.

## Key Python 3.13 Features

### 1. Type Parameter Syntax (PEP 695)

Python 3.13 introduces a cleaner syntax for generic type parameters:

#### Before (Python 3.12)
```python
from typing import TypeVar, Generic, List

T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')

class Repository(Generic[T]):
    def __init__(self) -> None:
        self._items: List[T] = []
    
    def add(self, item: T) -> None:
        self._items.append(item)

class Cache(Generic[K, V]):
    def __init__(self) -> None:
        self._data: dict[K, V] = {}
```

#### After (Python 3.13)
```python
# No need for separate TypeVar declarations
class Repository[T]:
    def __init__(self) -> None:
        self._items: list[T] = []
    
    def add(self, item: T) -> None:
        self._items.append(item)

class Cache[K, V]:
    def __init__(self) -> None:
        self._data: dict[K, V] = {}
```

### 2. Type Alias Improvements

#### Before
```python
from typing import TypeAlias, Union, Optional

UserId: TypeAlias = str
TripId: TypeAlias = str
Result: TypeAlias = Union[dict, list, None]
OptionalStr: TypeAlias = Optional[str]
```

#### After
```python
# Direct type alias syntax
type UserId = str
type TripId = str
type Result = dict | list | None
type OptionalStr = str | None
```

### 3. Enhanced Error Messages

Python 3.13 provides more informative error messages:

```python
# Better error messages for type mismatches
def process_trip(trip_id: TripId, user_id: UserId) -> None:
    pass

# Calling with wrong types now shows clearer errors:
process_trip(123, 456)  # Error clearly shows expected str, got int
```

### 4. Performance Improvements

- **Faster startup**: ~10% improvement in interpreter startup time
- **Optimized imports**: Lazy loading for standard library modules
- **Better memory management**: Reduced memory usage for class instances

## Migration Examples

### Service Classes

#### Before
```python
from typing import TypeVar, Generic, Optional, List, Dict, Any
from abc import ABC, abstractmethod

T = TypeVar('T', bound='BaseModel')

class BaseService(Generic[T], ABC):
    def __init__(self, repository: 'Repository[T]'):
        self.repository = repository
    
    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[T]:
        pass

class TripService(BaseService['Trip']):
    async def get_by_id(self, id: str) -> Optional['Trip']:
        return await self.repository.find_one(id)
```

#### After
```python
from abc import ABC, abstractmethod

class BaseService[T: BaseModel](ABC):
    def __init__(self, repository: Repository[T]):
        self.repository = repository
    
    @abstractmethod
    async def get_by_id(self, id: str) -> T | None:
        pass

class TripService(BaseService[Trip]):
    async def get_by_id(self, id: str) -> Trip | None:
        return await self.repository.find_one(id)
```

### Repository Pattern

#### Before
```python
from typing import TypeVar, Generic, List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar('T', bound='BaseModel')

class BaseRepository(Generic[T]):
    def __init__(self, session: AsyncSession, model_class: type[T]):
        self.session = session
        self.model_class = model_class
    
    async def find_all(self, filters: Dict[str, Any]) -> List[T]:
        # Implementation
        pass
    
    async def find_one(self, id: str) -> Optional[T]:
        # Implementation
        pass
```

#### After
```python
from sqlalchemy.ext.asyncio import AsyncSession

class BaseRepository[T: BaseModel]:
    def __init__(self, session: AsyncSession, model_class: type[T]):
        self.session = session
        self.model_class = model_class
    
    async def find_all(self, filters: dict[str, Any]) -> list[T]:
        # Implementation
        pass
    
    async def find_one(self, id: str) -> T | None:
        # Implementation
        pass
```

### API Response Types

#### Before
```python
from typing import TypeVar, Generic, Optional, Union
from pydantic import BaseModel

T = TypeVar('T')

class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    
class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    per_page: int
```

#### After
```python
from pydantic import BaseModel

class ApiResponse[T](BaseModel):
    success: bool
    data: T | None = None
    error: str | None = None
    
class PaginatedResponse[T](BaseModel):
    items: list[T]
    total: int
    page: int
    per_page: int
```

### Advanced Generic Constraints

#### Before
```python
from typing import TypeVar, Protocol, runtime_checkable

@runtime_checkable
class Cacheable(Protocol):
    def cache_key(self) -> str: ...

TCacheable = TypeVar('TCacheable', bound=Cacheable)

class CacheManager(Generic[TCacheable]):
    def __init__(self):
        self._cache: Dict[str, TCacheable] = {}
    
    def store(self, item: TCacheable) -> None:
        self._cache[item.cache_key()] = item
```

#### After
```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Cacheable(Protocol):
    def cache_key(self) -> str: ...

class CacheManager[T: Cacheable]:
    def __init__(self):
        self._cache: dict[str, T] = {}
    
    def store(self, item: T) -> None:
        self._cache[item.cache_key()] = item
```

## Performance Optimization Patterns

### 1. Lazy Imports

```python
# Defer heavy imports until needed
def process_data():
    # Import only when function is called
    import numpy as np
    import pandas as pd
    
    # Process data...
```

### 2. Union Type Optimization

```python
# Python 3.13 optimizes union type checking
def handle_result(result: dict | list | str | None) -> str:
    match result:
        case dict():
            return "dictionary"
        case list():
            return "list"
        case str():
            return "string"
        case None:
            return "none"
```

### 3. Pattern Matching with Types

```python
# Enhanced pattern matching with type parameters
def process_response[T](response: ApiResponse[T]) -> T:
    match response:
        case ApiResponse(success=True, data=data) if data is not None:
            return data
        case ApiResponse(success=False, error=error):
            raise ValueError(f"API error: {error}")
        case _:
            raise ValueError("Invalid response")
```

## Migration Checklist

### Code Updates

- [ ] Replace `TypeVar` declarations with inline type parameters
- [ ] Update `Generic[T]` base classes to use `[T]` syntax
- [ ] Replace `Optional[T]` with `T | None`
- [ ] Replace `Union[A, B]` with `A | B`
- [ ] Update type aliases to use `type` keyword
- [ ] Remove unnecessary `from typing import` statements

### Configuration Updates

- [ ] Update `pyproject.toml`:
  - Set `requires-python = ">=3.13"`
  - Set `target-version = "py313"` in ruff config
- [ ] Update CI/CD pipelines to use Python 3.13
- [ ] Update Docker images to Python 3.13-slim
- [ ] Update development environment documentation

### Testing

- [ ] Run full test suite with Python 3.13
- [ ] Verify type checking with mypy
- [ ] Check for deprecation warnings
- [ ] Benchmark performance improvements
- [ ] Test with production-like workloads

## Common Pitfalls

### 1. Circular Import Issues

```python
# Avoid circular imports with type parameters
# Use TYPE_CHECKING guard when necessary
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .repository import Repository

class Service[T]:
    def __init__(self, repo: 'Repository[T]'):
        self.repo = repo
```

### 2. Backward Compatibility

```python
# For libraries supporting multiple Python versions
import sys

if sys.version_info >= (3, 13):
    # Use new syntax
    class Container[T]: ...
else:
    # Fall back to old syntax
    from typing import TypeVar, Generic
    T = TypeVar('T')
    class Container(Generic[T]): ...
```

### 3. Type Parameter Scope

```python
# Type parameters are scoped to their declaration
class Outer[T]:
    # This inner class has its own T, not the same as Outer's T
    class Inner[T]:
        pass
    
    # To use Outer's T in Inner:
    class InnerCorrect:
        def process(self, item: T) -> T:  # Uses Outer's T
            return item
```

## Performance Benchmarks

### Startup Time Improvement

```python
# benchmark_startup.py
import time
import subprocess
import statistics

def measure_startup():
    times = []
    for _ in range(100):
        start = time.perf_counter()
        subprocess.run([sys.executable, "-c", "pass"], capture_output=True)
        times.append(time.perf_counter() - start)
    return statistics.mean(times)

# Python 3.12: ~0.025s average
# Python 3.13: ~0.022s average (12% improvement)
```

### Type Checking Performance

```python
# Type checking with unions is faster in Python 3.13
def check_types(value: int | str | list | dict | None) -> str:
    # Python 3.13 optimizes these checks
    if isinstance(value, int):
        return "integer"
    elif isinstance(value, str):
        return "string"
    # ... etc
```

## Best Practices

### 1. Use Descriptive Type Parameters

```python
# Good: Clear what each type parameter represents
class Cache[TKey, TValue]:
    pass

class Repository[TEntity: BaseModel]:
    pass

# Less clear
class Cache[K, V]:
    pass
```

### 2. Leverage Type Constraints

```python
# Constrain type parameters when appropriate
class NumberProcessor[T: (int, float)]:
    def process(self, value: T) -> T:
        return value * 2

class ModelRepository[T: BaseModel]:
    def save(self, entity: T) -> T:
        # Type checker knows T has BaseModel methods
        return entity.model_copy()
```

### 3. Consistent Type Alias Usage

```python
# Define common type aliases at module level
type UserId = str
type TripId = str
type Timestamp = float
type JsonDict = dict[str, Any]

# Use consistently throughout the module
async def get_user_trips(user_id: UserId) -> list[TripId]:
    pass
```

## Summary

Python 3.13 modernization brings:

- ✅ **Cleaner Syntax**: More readable generic type definitions
- ✅ **Better Performance**: Faster startup and runtime optimizations  
- ✅ **Enhanced Type Safety**: Improved type checking and error messages
- ✅ **Modern Patterns**: Aligned with current Python best practices
- ✅ **Future Ready**: Prepared for upcoming Python enhancements

This modernization aligns with TripSage's commitment to using cutting-edge technology while maintaining code quality and performance standards.