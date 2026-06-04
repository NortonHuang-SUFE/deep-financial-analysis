"""LangGraph entrypoint for the Task 3 assumption generator."""

from __future__ import annotations

from single_stock_coverage_agent.factory import create_graph


graph = create_graph("assumption_generator")

