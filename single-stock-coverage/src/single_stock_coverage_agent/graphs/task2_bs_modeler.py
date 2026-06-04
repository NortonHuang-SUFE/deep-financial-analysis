"""LangGraph entrypoint for the Task 2 Balance Sheet modeler."""

from __future__ import annotations

from single_stock_coverage_agent.factory import create_graph


graph = create_graph("bs_modeler")

