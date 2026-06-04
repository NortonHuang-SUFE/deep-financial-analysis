"""LangGraph entrypoint for the Task 3 DCF execution subagent."""

from __future__ import annotations

from single_stock_coverage_agent.factory import create_graph


graph = create_graph("dcf_execution")

