"""Example Custom Tool Plugin for ROMS.

To add new MCP tools to ROMS, simply create a python file in custom_tools/
and define a register_tools(mcp) function.
"""

from app.mcp_annotations import tool_annotations

def register_tools(mcp):
    """Registers custom tools directly into the ROMS FastMCP engine."""

    @mcp.tool(annotations=tool_annotations('calculate_refund_amount'))
    def calculate_refund_amount(item_price: float, return_shipping_fee: float = 0.0) -> str:
        """Calculates final refund amount after deducting return shipping.

        Pure arithmetic only: no payment provider, funds transfer, account access,
        network call, or persistent change. Returns an estimate, never issues a refund.
        """
        import math
        if not all(math.isfinite(v) and v >= 0 for v in (item_price, return_shipping_fee)):
            raise ValueError("Prices and fees must be finite, nonnegative numbers")
        total = max(0.0, item_price - return_shipping_fee)
        return f"Final refundable amount: ${total:.2f} (Original: ${item_price:.2f}, Shipping Fee: ${return_shipping_fee:.2f})"
