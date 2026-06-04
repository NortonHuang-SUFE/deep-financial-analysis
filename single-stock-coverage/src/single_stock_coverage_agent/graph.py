"""Single Stock Coverage - top-level LangGraph entrypoint."""

from __future__ import annotations

from single_stock_coverage_agent.agent_registry import ROOT_AGENT_NAME
from single_stock_coverage_agent.factory import create_graph


graph = create_graph(ROOT_AGENT_NAME)
