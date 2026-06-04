"""LangGraph entrypoint for Task 5 report assembly."""

from __future__ import annotations

from single_stock_coverage_agent.factory import create_graph


graph = create_graph("task5_report_assembler")
