"""Run-scoped runtime context middleware shared by every agent graph.

Each agent appends a "Runtime Context" block (Beijing time, artifact roots,
output-path rules) to its system prompt. Computing that block per model call
made the system message differ on every turn, which is fatal for the implicit
prefix caches these providers use: the cache matches from the start of the
request, so a changed timestamp in the first message invalidates the whole
conversation history behind it. Snapshotting the block once per graph
invocation keeps the system message byte-identical for the life of a run while
still giving each new run a fresh clock.
"""

from __future__ import annotations

from typing import Annotated, Any, Callable, NotRequired

from .concurrency import _agent_middleware_base


RUNTIME_CONTEXT_STATE_KEY = "runtime_context"


def keep_first_runtime_context(existing: str | None, incoming: str | None) -> str | None:
    """Fold concurrent writes to the snapshot instead of rejecting them.

    A plain state key is a ``LastValue`` channel, which raises
    ``InvalidUpdateError`` as soon as two branches write it in one superstep.
    That happens whenever the coordinator fans out to more than one subagent in
    a single turn: each subagent graph carries this middleware, so each one
    writes its own snapshot back in the same step. Folding with "first value
    wins" keeps the semantics ``before_agent`` already implements — an existing
    snapshot is never replaced — while making the concurrent case legal.
    """
    return existing or incoming


def make_runtime_context_middleware(context_factory: Callable[[], str]):
    """Return an ``AgentMiddleware`` that appends a run-scoped runtime context.

    Add this **once** to each agent's ``middleware=[...]`` list. The context is
    built by ``context_factory`` at the start of every graph invocation and
    stored in agent state, so all model calls in that run share one snapshot.
    Subagents are invoked as their own compiled graphs, so each subagent task
    gets its own snapshot, and concurrent runs never share one because the
    value only ever lives in per-invocation state.
    """
    base = _agent_middleware_base()

    class RunScopedRuntimeContextState(base.state_schema):  # type: ignore[misc, name-defined]
        runtime_context: NotRequired[Annotated[str, keep_first_runtime_context]]

    class RuntimeContextMiddleware(base):  # type: ignore[misc, valid-type]
        state_schema = RunScopedRuntimeContextState
        tools = []

        def before_agent(self, state: Any, runtime: Any) -> dict[str, Any] | None:
            # Keep an existing snapshot: a resumed run must not jump to a new
            # clock mid-conversation, which would break the cached prefix.
            if state.get(RUNTIME_CONTEXT_STATE_KEY):
                return None
            return {RUNTIME_CONTEXT_STATE_KEY: context_factory()}

        async def abefore_agent(self, state: Any, runtime: Any) -> dict[str, Any] | None:
            return self.before_agent(state, runtime)

        def wrap_model_call(self, request, handler):
            return handler(_request_with_runtime_context(request, context_factory))

        async def awrap_model_call(self, request, handler):
            return await handler(_request_with_runtime_context(request, context_factory))

    return RuntimeContextMiddleware()


def _request_with_runtime_context(request, context_factory: Callable[[], str]):
    """Append the run's runtime context snapshot to the request system prompt."""
    from langchain_core.messages import SystemMessage

    base_prompt = request.system_prompt or ""
    return request.override(
        system_message=SystemMessage(
            content=base_prompt + _runtime_context_for(request, context_factory)
        )
    )


def _runtime_context_for(request, context_factory: Callable[[], str]) -> str:
    """Return the run's snapshot, falling back to a fresh build when absent.

    The snapshot carries the artifact roots and date rules the agent needs to
    write anything at all, so a missing state key costs one cache miss rather
    than dropping the context.
    """
    state = getattr(request, "state", None) or {}
    snapshot = state.get(RUNTIME_CONTEXT_STATE_KEY)
    return snapshot if snapshot else context_factory()
