"""Shared runtime helpers for the financial services agent workspace."""

from __future__ import annotations

import atexit
import hashlib
import os
import re
import shlex
import shutil
import tempfile
import threading
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable
from urllib.parse import urlparse, urlunparse

from .concurrency import (
    load_and_register_mcp_tools,
    load_tool_concurrency_config,
    make_concurrency_limit_middleware,
    register_limited_tools,
    resolve_tool_group,
)
from .mcp_config import (
    MCPServerConfig,
    MCPToolGroupConfig,
    MX_DS_MCP_SERVER_NAME,
    MX_DS_MCP_URL,
    apply_mcp_env_overrides,
    default_mcp_tool_groups,
    enabled_mcp_server_configs,
    ifind_auth_headers,
    mcp_server_names_from_patterns,
    mcp_servers_from_yaml_data,
    mcp_tool_group_server_names,
    mx_ds_auth_headers,
)


DEFAULT_DAYTONA_FILE_STORAGE_ROOT = "/home/daytona/financial-analysis"

_DAYTONA_BACKEND = None
_GENERAL_PURPOSE_SUBAGENT_DISABLED_KEYS: set[str] = set()
_GENERAL_PURPOSE_SUBAGENT_LOCK = threading.Lock()
_SKILLS_UPLOAD_MAX_BYTES = 512 * 1024
_SKILLS_UPLOAD_MAX_FILES = 20
_OPENAI_API_VERSION_PATH_RE = re.compile(
    r"(^|/)(?:api/)?v\d+(?:/|$)", re.IGNORECASE
)
_TIMESTAMP_DIR_RE = re.compile(r"\d{8}-\d{6}(?:-\d+)?")


__all__ = [
    "DEFAULT_DAYTONA_FILE_STORAGE_ROOT",
    "MCPServerConfig",
    "MCPToolGroupConfig",
    "MX_DS_MCP_SERVER_NAME",
    "MX_DS_MCP_URL",
    "artifact_exists",
    "apply_mcp_env_overrides",
    "backend_is_daytona",
    "build_backend",
    "contains_task_timestamp_dir",
    "copy_artifact",
    "default_mcp_tool_groups",
    "ensure_artifact_dir",
    "ensure_general_purpose_subagent_disabled",
    "enabled_mcp_server_configs",
    "file_storage_root",
    "ifind_auth_headers",
    "list_artifact_dir",
    "load_and_register_mcp_tools",
    "load_tool_concurrency_config",
    "make_concurrency_limit_middleware",
    "materialize_file_artifact",
    "mirror_skills_into_backend",
    "mcp_server_names_from_patterns",
    "mcp_servers_from_yaml_data",
    "mcp_tool_group_server_names",
    "mx_ds_auth_headers",
    "normalize_openai_compatible_base_url",
    "read_bytes_artifact",
    "read_text_artifact",
    "register_limited_tools",
    "resolve_tool_group",
    "upload_file_artifact",
    "write_bytes_artifact",
    "write_text_artifact",
]


def backend_is_daytona() -> bool:
    """Return whether workspace agents should use the Daytona backend."""
    return os.getenv("AGENT_BACKEND", "local").strip().lower() == "daytona"


def file_storage_root(workspace_root: Path) -> Path:
    """Return the shared artifact storage root for a workspace."""
    if backend_is_daytona():
        raw_root = os.getenv("DAYTONA_FILE_STORAGE_ROOT")
        sandbox_root = (
            DEFAULT_DAYTONA_FILE_STORAGE_ROOT if raw_root is None else raw_root.strip()
        )
        _validate_daytona_root(sandbox_root)
        return Path(sandbox_root)

    raw_root = os.getenv("AGENT_FILE_STORAGE_ROOT")
    if not raw_root:
        return Path(workspace_root)

    path = Path(raw_root).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (Path(workspace_root) / path).resolve()


def normalize_openai_compatible_base_url(base_url: str) -> str:
    """Return a ChatOpenAI base URL without corrupting explicit API versions."""
    normalized = base_url.strip().rstrip("/")
    parsed = urlparse(normalized)
    path = parsed.path.rstrip("/")
    if _OPENAI_API_VERSION_PATH_RE.search(path.lstrip("/")):
        return normalized

    path = f"{path}/v1" if path else "/v1"
    return urlunparse(parsed._replace(path=path))


def build_backend(workspace_root: Path, prefer_shell: bool = True):
    """Return the configured deep-agents backend for local or Daytona mode."""
    if backend_is_daytona():
        return _daytona_backend()

    from deepagents.backends import FilesystemBackend, LocalShellBackend

    root = str(file_storage_root(workspace_root))
    if prefer_shell:
        return LocalShellBackend(root_dir=root, virtual_mode=False, inherit_env=True)
    return FilesystemBackend(root_dir=root, virtual_mode=False)


def mirror_skills_into_backend(backend: Any, local_dir: str | Path, storage_root: Path) -> str:
    """Return a backend-readable skills path, uploading local skills for Daytona."""
    local_dir = Path(local_dir)
    if not backend_is_daytona():
        return str(local_dir)
    if not local_dir.is_dir():
        return str(local_dir)

    storage_root_posix = _absolute_posix_path(storage_root, "storage_root")
    key = hashlib.sha1(str(local_dir.resolve()).encode()).hexdigest()[:12]
    dest_root = str(PurePosixPath(storage_root_posix) / ".skills" / f"{local_dir.name}-{key}")

    files = [
        (f"{dest_root}/{p.relative_to(local_dir).as_posix()}", p.read_bytes())
        for p in sorted(local_dir.rglob("*"))
        if p.is_file()
    ]
    if files:
        parents = sorted({str(PurePosixPath(dest).parent) for dest, _ in files})
        mkdir_response = backend.execute(
            "mkdir -p " + " ".join(shlex.quote(parent) for parent in parents)
        )
        _raise_backend_error(mkdir_response, "create skill directories")
        _upload_skill_files_in_chunks(backend, files)
        print(f"INFO: synced {len(files)} skill files -> {dest_root}")
    return dest_root


def ensure_artifact_dir(path: str | Path) -> None:
    """Ensure an artifact directory exists locally or in the Daytona sandbox."""
    if backend_is_daytona():
        remote_path = _absolute_posix_path(path, "artifact directory")
        response = _daytona_backend().execute("mkdir -p " + shlex.quote(remote_path))
        _raise_backend_error(response, f"create artifact directory {remote_path}")
        return

    Path(path).mkdir(parents=True, exist_ok=True)


def write_text_artifact(path: str | Path, text: str, encoding: str = "utf-8") -> None:
    """Write text to a local or Daytona artifact path."""
    write_bytes_artifact(path, text.encode(encoding))


def write_bytes_artifact(path: str | Path, data: bytes) -> None:
    """Write bytes to a local or Daytona artifact path."""
    if backend_is_daytona():
        remote_path = _absolute_posix_path(path, "artifact path")
        ensure_artifact_dir(str(PurePosixPath(remote_path).parent))
        response = _daytona_backend().upload_files([(remote_path, data)])
        _raise_backend_error(response, f"upload artifact {remote_path}")
        return

    local_path = Path(path)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(data)


def upload_file_artifact(local_path: str | Path, remote_path: str | Path) -> None:
    """Upload or copy a local file into an artifact destination."""
    source = Path(local_path)
    if backend_is_daytona():
        dest = _absolute_posix_path(remote_path, "artifact path")
        ensure_artifact_dir(str(PurePosixPath(dest).parent))
        response = _daytona_backend().upload_files([(dest, source.read_bytes())])
        _raise_backend_error(response, f"upload artifact {dest}")
        return

    dest_path = Path(remote_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest_path)


def read_bytes_artifact(path: str | Path, *, missing_ok: bool = False) -> bytes | None:
    """Read bytes from a local or Daytona artifact path.

    With ``missing_ok=True`` a missing file returns ``None`` instead of raising.
    """
    if backend_is_daytona():
        remote_path = _absolute_posix_path(path, "artifact path")
        responses = _daytona_backend().download_files([remote_path])
        response = responses[0] if isinstance(responses, (list, tuple)) else responses
        error = _response_text(response, "error")
        if error:
            if missing_ok and error == "file_not_found":
                return None
            raise RuntimeError(f"Failed to read artifact {remote_path}: {error}")
        content = (
            response.get("content")
            if isinstance(response, dict)
            else getattr(response, "content", None)
        )
        if content is None:
            if missing_ok:
                return None
            raise RuntimeError(f"Failed to read artifact {remote_path}: empty response")
        return content

    local_path = Path(path)
    if missing_ok and not local_path.exists():
        return None
    return local_path.read_bytes()


def read_text_artifact(
    path: str | Path, encoding: str = "utf-8", *, missing_ok: bool = False
) -> str | None:
    """Read text from a local or Daytona artifact path."""
    data = read_bytes_artifact(path, missing_ok=missing_ok)
    if data is None:
        return None
    return data.decode(encoding)


def artifact_exists(path: str | Path) -> bool:
    """Return whether a path exists locally or in the Daytona sandbox."""
    if backend_is_daytona():
        remote_path = _absolute_posix_path(path, "artifact path")
        response = _daytona_backend().execute("test -e " + shlex.quote(remote_path))
        return _execute_exit_code(response) == 0
    return Path(path).exists()


def list_artifact_dir(path: str | Path, *, missing_ok: bool = True) -> list[Path]:
    """Return immediate children of a directory locally or in the Daytona sandbox."""
    if backend_is_daytona():
        remote_path = _absolute_posix_path(path, "artifact directory")
        if not artifact_exists(remote_path):
            if missing_ok:
                return []
            raise RuntimeError(f"Artifact directory not found: {remote_path}")
        response = _daytona_backend().execute(
            "find " + shlex.quote(remote_path) + " -mindepth 1 -maxdepth 1 -print"
        )
        _raise_backend_error(response, f"list artifact directory {remote_path}")
        output = _response_text(response, "output") or ""
        return [Path(line) for line in output.splitlines() if line.strip()]

    local_path = Path(path)
    if not local_path.exists():
        if missing_ok:
            return []
        raise RuntimeError(f"Artifact directory not found: {local_path}")
    return list(local_path.iterdir())


def copy_artifact(source: str | Path, dest: str | Path) -> None:
    """Copy a file between two artifact paths within the same backend.

    Unlike :func:`upload_file_artifact` (host -> sandbox), both paths live on the
    active backend, so Daytona copies sandbox-to-sandbox via ``cp``.
    """
    if backend_is_daytona():
        remote_source = _absolute_posix_path(source, "artifact path")
        remote_dest = _absolute_posix_path(dest, "artifact path")
        ensure_artifact_dir(str(PurePosixPath(remote_dest).parent))
        response = _daytona_backend().execute(
            "cp " + shlex.quote(remote_source) + " " + shlex.quote(remote_dest)
        )
        _raise_backend_error(response, f"copy artifact {remote_source} -> {remote_dest}")
        return

    dest_path = Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(source), dest_path)


def materialize_file_artifact(dest: str | Path, producer: Callable[[Path], Any]) -> Any:
    """Build a file via ``producer(local_path)`` and place it at ``dest``.

    The producer always runs against a real local path, so any post-write step
    (e.g. patching a workbook) happens before the file is delivered. In Daytona
    mode the file is produced in a host temp file and then uploaded into the
    sandbox; locally the producer writes ``dest`` directly. Returns whatever the
    producer returns.
    """
    if backend_is_daytona():
        suffix = PurePosixPath(str(dest)).suffix
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            temp_path = Path(tmp.name)
        try:
            result = producer(temp_path)
            upload_file_artifact(temp_path, dest)
            return result
        finally:
            temp_path.unlink(missing_ok=True)

    dest_path = Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    return producer(dest_path)


def contains_task_timestamp_dir(path: str | Path) -> bool:
    """Return whether the leaf or direct parent is a task timestamp directory."""
    candidate = Path(path)
    if _TIMESTAMP_DIR_RE.fullmatch(candidate.name):
        return True

    parent_name = candidate.parent.name
    return bool(parent_name and _TIMESTAMP_DIR_RE.fullmatch(parent_name))


def ensure_general_purpose_subagent_disabled(model: Any | None = None) -> None:
    """Idempotently disable Deep Agents' auto-added general-purpose subagent."""
    key = _harness_profile_key(model)
    with _GENERAL_PURPOSE_SUBAGENT_LOCK:
        if key in _GENERAL_PURPOSE_SUBAGENT_DISABLED_KEYS:
            return

        from deepagents import (
            GeneralPurposeSubagentProfile,
            HarnessProfile,
            register_harness_profile,
        )

        register_harness_profile(
            key,
            HarnessProfile(
                general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
            ),
        )
        _GENERAL_PURPOSE_SUBAGENT_DISABLED_KEYS.add(key)


def _daytona_backend():
    """Return a process-wide shared Daytona sandbox backend."""
    global _DAYTONA_BACKEND
    if _DAYTONA_BACKEND is None:
        from daytona import Daytona
        from langchain_daytona import DaytonaSandbox

        client = Daytona()
        shared_id = os.environ.get("_DAYTONA_SHARED_SANDBOX_ID")
        if shared_id:
            sandbox = client.get(shared_id)
        else:
            sandbox = client.create()
            os.environ["_DAYTONA_SHARED_SANDBOX_ID"] = sandbox.id
            if os.getenv("DAYTONA_KEEP_SANDBOX") != "1":
                atexit.register(_delete_daytona_sandbox, client, sandbox)
        _DAYTONA_BACKEND = DaytonaSandbox(sandbox=sandbox)
    return _DAYTONA_BACKEND


def _delete_daytona_sandbox(client: Any, sandbox: Any) -> None:
    try:
        client.delete(sandbox)
    except Exception:
        pass


def _upload_skill_files_in_chunks(backend: Any, files: Iterable[tuple[str, bytes]]) -> None:
    batch: list[tuple[str, bytes]] = []
    batch_bytes = 0
    for path, content in files:
        if batch and (
            len(batch) >= _SKILLS_UPLOAD_MAX_FILES
            or batch_bytes + len(content) > _SKILLS_UPLOAD_MAX_BYTES
        ):
            response = backend.upload_files(batch)
            _raise_backend_error(response, "upload skill files")
            batch, batch_bytes = [], 0
        batch.append((path, content))
        batch_bytes += len(content)

    if batch:
        response = backend.upload_files(batch)
        _raise_backend_error(response, "upload skill files")


def _validate_daytona_root(path: str) -> None:
    if not path or not path.startswith("/") or not PurePosixPath(path).is_absolute():
        raise ValueError(
            "DAYTONA_FILE_STORAGE_ROOT must be an absolute POSIX path starting "
            f"with '/'; got {path!r}."
        )


def _absolute_posix_path(path: str | Path, label: str) -> str:
    value = str(path).strip()
    if not value or not value.startswith("/") or not PurePosixPath(value).is_absolute():
        raise ValueError(f"{label} must be an absolute POSIX path; got {value!r}.")
    return value


def _raise_backend_error(response: Any, action: str) -> None:
    error = _backend_error(response)
    if error:
        raise RuntimeError(f"Failed to {action}: {error}")


def _backend_error(response: Any) -> str | None:
    if response is None:
        return None

    if isinstance(response, int):
        return None if response == 0 else f"exit code {response}"

    if isinstance(response, dict):
        error = response.get("error")
        if error:
            return str(error)
        for flag in ("success", "ok"):
            if response.get(flag) is False:
                return _response_text(response, "stderr") or f"{flag} is False"
        for key in ("exit_code", "returncode", "return_code", "code", "exitCode"):
            error = _exit_code_error(response.get(key), response)
            if error:
                return error
        return None

    if isinstance(response, (list, tuple)):
        for item in response:
            error = _backend_error(item)
            if error:
                return error
        return None

    error = getattr(response, "error", None)
    if error:
        return str(error)

    for flag in ("success", "ok"):
        if getattr(response, flag, None) is False:
            return _response_text(response, "stderr") or f"{flag} is False"

    for attr in ("exit_code", "returncode", "return_code", "code", "exitCode"):
        error = _exit_code_error(getattr(response, attr, None), response)
        if error:
            return error
    return None


def _execute_exit_code(response: Any) -> int | None:
    """Return a command's exit code without treating non-zero as an error."""
    if isinstance(response, int):
        return response
    if isinstance(response, dict):
        for key in ("exit_code", "returncode", "return_code", "code", "exitCode"):
            value = response.get(key)
            if isinstance(value, int):
                return value
        return None
    for attr in ("exit_code", "returncode", "return_code", "code", "exitCode"):
        value = getattr(response, attr, None)
        if isinstance(value, int):
            return value
    return None


def _exit_code_error(code: Any, response: Any) -> str | None:
    if not isinstance(code, int) or code == 0:
        return None

    stderr = _response_text(response, "stderr") or _response_text(response, "error")
    if stderr:
        return f"exit code {code}: {stderr}"
    return f"exit code {code}"


def _response_text(response: Any, key: str) -> str | None:
    if isinstance(response, dict):
        value = response.get(key)
    else:
        value = getattr(response, key, None)
    return str(value) if value else None


def _harness_profile_key(model: Any | None) -> str:
    provider = None
    if model is not None:
        try:
            from deepagents._models import get_model_provider

            provider = get_model_provider(model)
        except Exception:
            provider = None
    return provider or "openai"
