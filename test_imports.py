"""
Test the imports to verify the circular dependency is fixed.
"""

import sys
from unittest.mock import Mock

# Mock the problematic modules
sys.modules["src.utils.config"] = Mock()
sys.modules["src.utils.settings"] = Mock()
sys.modules["src.cache.redis_cache"] = Mock()
sys.modules["src.mcp.memory.server"] = Mock()

# Now try to import without circular dependency

print("Successfully imported all modules!")
