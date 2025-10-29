"""Performance testing for outbound HTTP utilities.

This module provides benchmarks for outbound request handling,
ensuring async patterns don't block the event loop.
"""

import asyncio
import time
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from tests.performance.test_api_key_performance import BenchmarkFixture
from tripsage_core.utils.outbound import request_with_backoff


class TestOutboundPerformance:
    """Performance tests for outbound utilities."""

    @pytest.fixture
    def mock_client(self):
        """Mock httpx client for testing."""
        client = AsyncMock(spec=httpx.AsyncClient)
        response = AsyncMock(spec=httpx.Response)
        response.status_code = 200
        response.headers = {}
        client.request.return_value = response
        return client

    @pytest.mark.asyncio
    async def test_request_with_backoff_no_blocking(
        self, mock_client: AsyncMock, benchmark: BenchmarkFixture
    ):
        """Benchmark request_with_backoff to ensure no event loop blocking."""

        async def run_request():
            return await request_with_backoff(
                mock_client,
                "GET",
                "https://api.example.com/test",
                max_retries=0,
            )

        # Benchmark the async call
        result = await benchmark(run_request)
        assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_concurrent_requests_no_blocking(self):
        """Test concurrent requests don't block each other."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            response = AsyncMock()
            response.status_code = 200
            response.headers = {}
            mock_client.request.return_value = response
            mock_client_class.return_value = mock_client

            async def make_request(i: int):
                client = httpx.AsyncClient()
                return await request_with_backoff(
                    client,
                    "GET",
                    f"https://api{i}.example.com/test",
                    max_retries=0,
                )

            # Run 10 concurrent requests
            start_time = time.time()
            tasks = [make_request(i) for i in range(10)]
            results = await asyncio.gather(*tasks)
            end_time = time.time()

            # Should complete quickly (under 0.1s since mocked)
            duration = end_time - start_time
            assert duration < 0.1, f"Requests took too long: {duration}s"
            assert all(r.status_code == 200 for r in results)
