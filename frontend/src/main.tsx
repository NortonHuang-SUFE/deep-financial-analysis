import { FormEvent, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { Client } from "@langchain/langgraph-sdk";
import {
  Activity,
  Bot,
  ChevronRight,
  CircleStop,
  ClipboardList,
  Cpu,
  Eraser,
  FileJson,
  Play,
  RefreshCw,
  Send,
  Sparkles,
  TerminalSquare,
  Wrench,
} from "lucide-react";
import "./styles.css";

type MessageItem = {
  id: string;
  scope: string;
  namespace: string;
  node?: string;
  text: string;
  status: "streaming" | "done" | "error";
  raw?: unknown;
};

type ToolItem = {
  id: string;
  scope: string;
  name: string;
  namespace: string;
  input: unknown;
  output?: unknown;
  status: "running" | "done" | "error";
};

type SubagentItem = {
  callId: string;
  name: string;
  namespace: string;
  taskInput: string;
  output?: unknown;
  status: "running" | "done" | "error";
  messages: MessageItem[];
  tools: ToolItem[];
};

type EventLogItem = {
  id: string;
  at: string;
  channel: string;
  label: string;
  data?: unknown;
};

const DEFAULT_ASSISTANT_ID = "daily_report";

const makeId = () =>
  typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;

const nowStamp = () =>
  new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date());

const toJson = (value: unknown) => {
  if (value === undefined) return "";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
};

const textFromContent = (content: unknown): string => {
  if (typeof content === "string") return content;
  if (!Array.isArray(content)) return "";
  return content
    .map((block) => {
      if (typeof block === "string") return block;
      if (!block || typeof block !== "object") return "";
      const item = block as Record<string, unknown>;
      if (typeof item.text === "string") return item.text;
      if (typeof item.content === "string") return item.content;
      return "";
    })
    .filter(Boolean)
    .join("\n");
};

function App() {
  const defaultApiUrl = useMemo(() => {
    const fromEnv = import.meta.env.VITE_LANGGRAPH_API_URL as string | undefined;
    return fromEnv || `${window.location.origin}/lg`;
  }, []);

  const [apiUrl, setApiUrl] = useState(defaultApiUrl);
  const [assistantId, setAssistantId] = useState(DEFAULT_ASSISTANT_ID);
  const [prompt, setPrompt] = useState(
    "请生成今天的 A 股盘前日报，并在完成 morning note 后生成一张头图。"
  );
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState("idle");
  const [threadId, setThreadId] = useState("");
  const [runId, setRunId] = useState("");
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [tools, setTools] = useState<ToolItem[]>([]);
  const [subagents, setSubagents] = useState<SubagentItem[]>([]);
  const [finalOutput, setFinalOutput] = useState<unknown>(undefined);
  const [events, setEvents] = useState<EventLogItem[]>([]);
  const activeThread = useRef<{ close: () => Promise<void> } | null>(null);
  const runToken = useRef("");

  const logEvent = (channel: string, label: string, data?: unknown) => {
    setEvents((items) =>
      [
        {
          id: makeId(),
          at: nowStamp(),
          channel,
          label,
          data,
        },
        ...items,
      ].slice(0, 240)
    );
  };

  const clearRun = () => {
    setThreadId("");
    setRunId("");
    setMessages([]);
    setTools([]);
    setSubagents([]);
    setFinalOutput(undefined);
    setEvents([]);
    setStatus("idle");
  };

  const appendMessage = (message: MessageItem, subagentCallId?: string) => {
    if (subagentCallId) {
      setSubagents((items) =>
        items.map((item) =>
          item.callId === subagentCallId
            ? {
                ...item,
                messages: item.messages.some((existing) => existing.id === message.id)
                  ? item.messages.map((existing) =>
                      existing.id === message.id
                        ? { ...existing, ...message, text: existing.text || message.text }
                        : existing
                    )
                  : [...item.messages, message],
              }
            : item
        )
      );
      return;
    }
    setMessages((items) =>
      items.some((existing) => existing.id === message.id)
        ? items.map((existing) =>
            existing.id === message.id
              ? { ...existing, ...message, text: existing.text || message.text }
              : existing
          )
        : [...items, message]
    );
  };

  const updateMessage = (
    id: string,
    patch: Partial<MessageItem>,
    subagentCallId?: string
  ) => {
    if (subagentCallId) {
      setSubagents((items) =>
        items.map((item) =>
          item.callId === subagentCallId
            ? {
                ...item,
                messages: item.messages.map((message) =>
                  message.id === id ? { ...message, ...patch } : message
                ),
              }
            : item
        )
      );
      return;
    }
    setMessages((items) =>
      items.map((message) =>
        message.id === id ? { ...message, ...patch } : message
      )
    );
  };

  const appendTool = (tool: ToolItem, subagentCallId?: string) => {
    if (subagentCallId) {
      setSubagents((items) =>
        items.map((item) =>
          item.callId === subagentCallId
            ? {
                ...item,
                tools: item.tools.some((existing) => existing.id === tool.id)
                  ? item.tools.map((existing) =>
                      existing.id === tool.id ? { ...existing, ...tool } : existing
                    )
                  : [...item.tools, tool],
              }
            : item
        )
      );
      return;
    }
    setTools((items) =>
      items.some((existing) => existing.id === tool.id)
        ? items.map((existing) => (existing.id === tool.id ? { ...existing, ...tool } : existing))
        : [...items, tool]
    );
  };

  const updateTool = (
    id: string,
    patch: Partial<ToolItem>,
    subagentCallId?: string
  ) => {
    if (subagentCallId) {
      setSubagents((items) =>
        items.map((item) =>
          item.callId === subagentCallId
            ? {
                ...item,
                tools: item.tools.map((tool) =>
                  tool.id === id ? { ...tool, ...patch } : tool
                ),
              }
            : item
        )
      );
      return;
    }
    setTools((items) =>
      items.map((tool) => (tool.id === id ? { ...tool, ...patch } : tool))
    );
  };

  const consumeMessages = async (
    source: AsyncIterable<any>,
    scope: string,
    token: string,
    subagentCallId?: string
  ) => {
    for await (const message of source) {
      if (runToken.current !== token) return;
      const id = `${scope}:${message.id || makeId()}`;
      const namespace = Array.isArray(message.namespace)
        ? message.namespace.join(" / ")
        : "";
      appendMessage(
        {
          id,
          scope,
          namespace,
          node: message.node,
          text: "",
          status: "streaming",
        },
        subagentCallId
      );

      let text = "";
      try {
        for await (const delta of message.text) {
          if (runToken.current !== token) return;
          text += delta;
          updateMessage(id, { text }, subagentCallId);
        }
        const output = await message.output;
        const finalText = text || textFromContent(output?.content);
        updateMessage(
          id,
          {
            text: finalText,
            status: "done",
            raw: output,
          },
          subagentCallId
        );
      } catch (error) {
        updateMessage(
          id,
          {
            status: "error",
            raw: error instanceof Error ? error.message : error,
          },
          subagentCallId
        );
      }
    }
  };

  const consumeTools = async (
    source: AsyncIterable<any>,
    scope: string,
    token: string,
    subagentCallId?: string
  ) => {
    for await (const tool of source) {
      if (runToken.current !== token) return;
      const id = `${scope}:${tool.callId || tool.id || makeId()}`;
      appendTool(
        {
          id,
          scope,
          name: tool.name,
          namespace: Array.isArray(tool.namespace)
            ? tool.namespace.join(" / ")
            : "",
          input: tool.input,
          status: "running",
        },
        subagentCallId
      );
      try {
        const output = await tool.output;
        updateTool(id, { output, status: "done" }, subagentCallId);
      } catch (error) {
        updateTool(
          id,
          {
            output: error instanceof Error ? error.message : error,
            status: "error",
          },
          subagentCallId
        );
      }
    }
  };

  const consumeValues = async (source: AsyncIterable<unknown>, token: string) => {
    for await (const value of source) {
      if (runToken.current !== token) return;
      setFinalOutput(value);
    }
  };

  const consumeSubagents = async (thread: any, token: string) => {
    for await (const subagent of thread.subagents) {
      if (runToken.current !== token) return;
      const callId = subagent.callId || makeId();
      const namespace = Array.isArray(subagent.namespace)
        ? subagent.namespace.join(" / ")
        : "";
      setSubagents((items) =>
        items.some((item) => item.callId === callId)
          ? items.map((item) =>
              item.callId === callId
                ? { ...item, name: subagent.name, namespace, status: "running" }
                : item
            )
          : [
              ...items,
              {
                callId,
                name: subagent.name,
                namespace,
                taskInput: "",
                status: "running",
                messages: [],
                tools: [],
              },
            ]
      );
      logEvent("subagent", `${subagent.name} started`, {
        callId,
        namespace: subagent.namespace,
      });

      void subagent.taskInput
        .then((taskInput: string) => {
          setSubagents((items) =>
            items.map((item) =>
              item.callId === callId ? { ...item, taskInput } : item
            )
          );
        })
        .catch(() => undefined);

      void consumeMessages(subagent.messages, subagent.name, token, callId);
      void consumeTools(subagent.toolCalls, subagent.name, token, callId);

      void subagent.output
        .then((output: unknown) => {
          setSubagents((items) =>
            items.map((item) =>
              item.callId === callId
                ? { ...item, output, status: "done" }
                : item
            )
          );
          logEvent("subagent", `${subagent.name} finished`, output);
        })
        .catch((error: unknown) => {
          setSubagents((items) =>
            items.map((item) =>
              item.callId === callId
                ? {
                    ...item,
                    output: error instanceof Error ? error.message : error,
                    status: "error",
                  }
                : item
            )
          );
        });
    }
  };

  const consumeRawEvents = async (thread: any, token: string) => {
    const subscription = await thread.subscribe({
      channels: ["lifecycle", "updates", "tasks"],
      depth: 16,
    });
    for await (const event of subscription) {
      if (runToken.current !== token) return;
      logEvent(event.method || "event", event.params?.data?.event || event.method, event);
    }
  };

  const runPrompt = async (event: FormEvent) => {
    event.preventDefault();
    const content = prompt.trim();
    if (!content || running) return;

    await activeThread.current?.close().catch(() => undefined);
    const token = makeId();
    runToken.current = token;
    clearRun();
    setRunning(true);
    setStatus("connecting");

    try {
      const client = new Client({
        apiUrl: apiUrl.trim().replace(/\/$/, ""),
      });
      const createdThread = await client.threads.create({
        metadata: {
          source: "daily-report-frontend",
          created_at: new Date().toISOString(),
        },
      });
      const thread = client.threads.stream(createdThread.thread_id, {
        assistantId: assistantId.trim() || DEFAULT_ASSISTANT_ID,
        transport: "sse",
      });
      activeThread.current = thread;
      setThreadId(createdThread.thread_id);

      void consumeMessages(thread.messages, "daily_report", token);
      void consumeTools(thread.toolCalls, "daily_report", token);
      void consumeValues(thread.values, token);
      void consumeSubagents(thread, token);
      void consumeRawEvents(thread, token).catch((error) => {
        logEvent("raw", "raw stream error", error instanceof Error ? error.message : error);
      });

      setStatus("running");
      const started = await thread.run.start({
        input: {
          messages: [{ role: "user", content }],
        },
        metadata: {
          source: "daily-report-frontend",
          started_at: new Date().toISOString(),
        },
      });
      setRunId(started.run_id || "");
      logEvent("run", "started", started);

      const output = await thread.output;
      if (runToken.current !== token) return;
      setFinalOutput(output);
      setStatus(thread.interrupted ? "interrupted" : "done");
      logEvent(thread.interrupted ? "run" : "output", thread.interrupted ? "interrupted" : "completed", output);
    } catch (error) {
      if (runToken.current !== token) return;
      setStatus("error");
      logEvent("error", "run failed", error instanceof Error ? error.message : error);
    } finally {
      if (runToken.current === token) {
        setRunning(false);
        await activeThread.current?.close().catch(() => undefined);
        activeThread.current = null;
      }
    }
  };

  const closeStream = async () => {
    runToken.current = makeId();
    setRunning(false);
    setStatus("closed");
    await activeThread.current?.close().catch(() => undefined);
    activeThread.current = null;
    logEvent("run", "stream closed by user");
  };

  const ping = async () => {
    try {
      setStatus("checking");
      const url = `${apiUrl.trim().replace(/\/$/, "")}/ok`;
      const response = await fetch(url);
      const body = await response.json();
      setStatus(body?.ok ? "ready" : "unknown");
      logEvent("health", response.ok ? "ok" : "not ok", body);
    } catch (error) {
      setStatus("offline");
      logEvent("health", "failed", error instanceof Error ? error.message : error);
    }
  };

  return (
    <main className="app-shell">
      <section className="topbar">
        <div>
          <div className="product-mark">
            <Sparkles size={18} />
            <span>Daily Report Console</span>
          </div>
          <h1>LangGraph 输出调试台</h1>
        </div>
        <div className={`status-pill status-${status}`}>
          <Activity size={16} />
          <span>{status}</span>
        </div>
      </section>

      <section className="workspace">
        <form className="composer" onSubmit={runPrompt}>
          <div className="field-grid">
            <label>
              <span>API</span>
              <input
                value={apiUrl}
                onChange={(event) => setApiUrl(event.target.value)}
                spellCheck={false}
              />
            </label>
            <label>
              <span>Assistant</span>
              <input
                value={assistantId}
                onChange={(event) => setAssistantId(event.target.value)}
                spellCheck={false}
              />
            </label>
          </div>

          <label className="prompt-field">
            <span>Prompt</span>
            <textarea
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              spellCheck={false}
            />
          </label>

          <div className="toolbar">
            <button type="submit" className="primary" disabled={running}>
              <Send size={17} />
              <span>运行</span>
            </button>
            <button type="button" onClick={closeStream} disabled={!running}>
              <CircleStop size={17} />
              <span>断开</span>
            </button>
            <button type="button" onClick={ping}>
              <RefreshCw size={17} />
              <span>检查</span>
            </button>
            <button type="button" onClick={clearRun} disabled={running}>
              <Eraser size={17} />
              <span>清空</span>
            </button>
          </div>

          <div className="run-meta">
            <span>thread: {threadId || "-"}</span>
            <span>run: {runId || "-"}</span>
          </div>
        </form>

        <section className="output-grid">
          <Panel
            icon={<Bot size={18} />}
            title="Coordinator"
            count={messages.length}
          >
            <MessageList messages={messages} empty="暂无 coordinator 消息" />
          </Panel>

          <Panel
            icon={<Cpu size={18} />}
            title="Subagents"
            count={subagents.length}
          >
            <SubagentList subagents={subagents} />
          </Panel>

          <Panel icon={<Wrench size={18} />} title="Tools" count={tools.length}>
            <ToolList tools={tools} empty="暂无 coordinator 工具调用" />
          </Panel>

          <Panel icon={<FileJson size={18} />} title="Final State">
            <pre className="json-view">{toJson(finalOutput) || "暂无最终状态"}</pre>
          </Panel>
        </section>

        <section className="event-strip">
          <div className="section-heading">
            <TerminalSquare size={18} />
            <h2>Event Stream</h2>
            <span>{events.length}</span>
          </div>
          <div className="event-list">
            {events.length === 0 ? (
              <p className="empty">暂无事件</p>
            ) : (
              events.map((item) => (
                <details key={item.id} className="event-row">
                  <summary>
                    <span>{item.at}</span>
                    <strong>{item.channel}</strong>
                    <em>{item.label}</em>
                  </summary>
                  <pre>{toJson(item.data)}</pre>
                </details>
              ))
            )}
          </div>
        </section>
      </section>
    </main>
  );
}

function Panel({
  icon,
  title,
  count,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  count?: number;
  children: React.ReactNode;
}) {
  return (
    <section className="panel">
      <div className="section-heading">
        {icon}
        <h2>{title}</h2>
        {typeof count === "number" ? <span>{count}</span> : null}
      </div>
      {children}
    </section>
  );
}

function MessageList({
  messages,
  empty,
}: {
  messages: MessageItem[];
  empty: string;
}) {
  if (messages.length === 0) return <p className="empty">{empty}</p>;
  return (
    <div className="message-list">
      {messages.map((message) => (
        <article key={message.id} className={`message-row ${message.status}`}>
          <div className="row-title">
            <ChevronRight size={15} />
            <strong>{message.node || message.scope}</strong>
            <span>{message.namespace || "root"}</span>
          </div>
          <p>{message.text || "..."}</p>
        </article>
      ))}
    </div>
  );
}

function ToolList({ tools, empty }: { tools: ToolItem[]; empty: string }) {
  if (tools.length === 0) return <p className="empty">{empty}</p>;
  return (
    <div className="tool-list">
      {tools.map((tool) => (
        <details key={tool.id} className={`tool-row ${tool.status}`}>
          <summary>
            <ClipboardList size={15} />
            <strong>{tool.name}</strong>
            <span>{tool.status}</span>
          </summary>
          <pre>{toJson({ input: tool.input, output: tool.output })}</pre>
        </details>
      ))}
    </div>
  );
}

function SubagentList({ subagents }: { subagents: SubagentItem[] }) {
  if (subagents.length === 0) return <p className="empty">暂无 subagent</p>;
  return (
    <div className="subagent-list">
      {subagents.map((subagent) => (
        <article key={subagent.callId} className={`subagent-row ${subagent.status}`}>
          <header>
            <div>
              <strong>{subagent.name}</strong>
              <span>{subagent.namespace || subagent.callId}</span>
            </div>
            <em>{subagent.status}</em>
          </header>
          {subagent.taskInput ? <p className="task-input">{subagent.taskInput}</p> : null}
          <MessageList messages={subagent.messages} empty="暂无 subagent 消息" />
          <ToolList tools={subagent.tools} empty="暂无 subagent 工具调用" />
          <details className="subagent-output">
            <summary>
              <Play size={14} />
              <span>output</span>
            </summary>
            <pre>{toJson(subagent.output) || "暂无输出"}</pre>
          </details>
        </article>
      ))}
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
