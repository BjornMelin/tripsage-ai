"""Test basic imports of the MCP abstraction layer after circular import fix."""


def test_mcp_abstraction_imports():
    """Test that all MCP abstraction components can be imported."""
    # Test main module imports
    from tripsage.mcp_abstraction import (
        BaseMCPWrapper,
        TripSageMCPError,
        mcp_manager,
        registry,
    )

    # Verify the objects exist
    assert BaseMCPWrapper is not None
    assert mcp_manager is not None
    assert registry is not None
    assert TripSageMCPError is not None

    print("✓ All MCP abstraction imports successful")


def test_manager_initialization():
    """Test that manager can be initialized without circular imports."""
    from tripsage.mcp_abstraction.manager import mcp_manager

    # Manager should exist
    assert mcp_manager is not None
    # Manager is an instance of MCPManager
    assert hasattr(mcp_manager, "invoke")
    assert hasattr(mcp_manager, "initialize_mcp")
    assert hasattr(mcp_manager, "get_available_mcps")

    print("✓ Manager initialization successful")


if __name__ == "__main__":
    test_mcp_abstraction_imports()
    test_manager_initialization()
    print("All basic import tests passed!")
