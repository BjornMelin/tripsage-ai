"""Shared pytest fixtures for TripSage tests."""

pytest_plugins = [
    "tests.fixtures.cache",
    "tests.fixtures.outbound",
    "tests.fixtures.settings",
]
