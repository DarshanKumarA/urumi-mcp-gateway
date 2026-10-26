import { useEffect, useState, type ReactNode } from "react";
import {
  api,
  type Server,
  type Tool,
  type User,
  type Key,
  type Audit,
  type Answer,
} from "./api";
import {
  Header,
  Status,
  Modal,
  Secret,
  Confirm,
  Empty,
  Failure,
  time,
} from "./components";
function useLoad<T>(path: string) {
  const [data, setData] = useState<T | null>(null),
    [error, setError] = useState(false),
    [loading, setLoading] = useState(true),
    [revision, setRevision] = useState(0);
  const reload = () => setRevision((v) => v + 1);
  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(false);
    api<T>(path)
      .then((v) => {
        if (alive) setData(v);
      })
      .catch(() => {
        if (alive) setError(true);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [path, revision]);
  return { data, error, loading, reload };
}
function Load({
  state,
  children,
}: {
  state: { loading: boolean; error: boolean; reload: () => void };
  children: ReactNode;
}) {
  return state.loading ? (
    <div role="status" className="empty">
      Loading…
    </div>
  ) : state.error ? (
    <Failure retry={state.reload} />
  ) : (
    <>{children}</>
  );
}
function Tools({ tools, stale = false }: { tools: Tool[]; stale?: boolean }) {
  return (
    <details>
      <summary>
        {tools.length} tools{stale ? " · cached" : ""}
      </summary>
      <ul className="tool-list">
        {tools.map((t) => (
          <li key={t.name}>
            <code>{t.name}</code>
            {t.description && <p>{t.description}</p>}
          </li>
        ))}
      </ul>
    </details>
  );
}
function ServerForm({
  server,
  onClose,
  onSave,
}: {
  server?: Server;
  onClose: () => void;
  onSave: () => void;
}) {
  const [name, setName] = useState(server?.display_name || ""),
    [slug, setSlug] = useState(server?.slug || ""),
    [url, setUrl] = useState(server?.url || "");
  const [mode, setMode] = useState("preserve"),
    [value, setValue] = useState(""),
    [header, setHeader] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  return (
    <Modal
      title={server ? "Edit server" : "Add server"}
      onClose={() => {
        if (!busy) onClose();
      }}
    >
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          if (busy) return;
          setBusy(true);
          setError("");
          const body: Record<string, unknown> = { display_name: name, url };
          if (!server) body.slug = slug;
          if (mode === "clear") body.credential = null;
          else if (mode === "bearer" || mode === "header")
            body.credential = {
              kind: mode,
              value,
              ...(mode === "header" ? { header_name: header } : {}),
            };
          try {
            await api(
              "/servers" + (server ? "/" + server.id : ""),
              body,
              server ? "PATCH" : "POST",
            );
            setValue("");
            onSave();
          } catch {
            setValue("");
            setError(
              "Server could not be saved. Check the URL, slug and credential settings.",
            );
            setBusy(false);
          }
        }}
      >
        <label>
          Display name
          <input
            value={name}
            required
            maxLength={100}
            onChange={(e) => setName(e.target.value)}
          />
        </label>
        <label>
          Server slug
          <input
            className="mono"
            value={slug}
            required
            disabled={!!server}
            pattern="[a-z][a-z0-9_]*"
            maxLength={32}
            onChange={(e) => setSlug(e.target.value)}
          />
          <small>Permanent namespace for this server's tools.</small>
        </label>
        <label>
          Streamable HTTP endpoint
          <input
            className="mono"
            value={url}
            required
            type="url"
            maxLength={2048}
            onChange={(e) => setUrl(e.target.value)}
          />
        </label>
        <label>
          Credential
          <select
            value={mode}
            onChange={(e) => {
              setMode(e.target.value);
              setValue("");
            }}
          >
            <option value="preserve">
              {server ? "Keep existing credential" : "No credential"}
            </option>
            <option value="bearer">Replace with Bearer token</option>
            <option value="header">Replace with static header</option>
            {server && <option value="clear">Remove credential</option>}
          </select>
        </label>
        {mode === "header" && (
          <label>
            Header name
            <input
              required
              value={header}
              onChange={(e) => setHeader(e.target.value)}
            />
          </label>
        )}
        {(mode === "bearer" || mode === "header") && (
          <label>
            New credential value
            <input
              required
              type="password"
              autoComplete="off"
              value={value}
              onChange={(e) => setValue(e.target.value)}
            />
            <small>Stored server-side. Never returned after saving.</small>
          </label>
        )}
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <div className="form-actions">
          <button type="button" disabled={busy} onClick={onClose}>
            Cancel
          </button>
          <button className="primary" disabled={busy}>
            {busy ? "Saving…" : "Save server"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
export function Servers({ admin }: { admin: boolean }) {
  const state = useLoad<Server[] | { tools: Tool[] }>(
    admin ? "/servers" : "/catalog",
  );
  const [edit, setEdit] = useState<Server | null | undefined>(undefined),
    [confirm, setConfirm] = useState<Server | null>(null),
    [busy, setBusy] = useState(""),
    [error, setError] = useState("");
  async function action(s: Server, verb: string) {
    setBusy(s.id);
    setError("");
    try {
      await api("/servers/" + s.id + "/" + verb, {});
      state.reload();
    } catch {
      setError(
        "Server action failed. Refresh the current state before retrying.",
      );
    } finally {
      setBusy("");
    }
  }
  return (
    <>
      <Header
        title="Servers"
        description={
          admin
            ? "Manage upstream connections and the tools available to your team."
            : "Tools currently available through your gateway."
        }
        action={
          admin && (
            <button className="primary" onClick={() => setEdit(null)}>
              Add server
            </button>
          )
        }
      />
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <Load state={state}>
        {admin ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  {[
                    "Server",
                    "Status",
                    "Endpoint",
                    "Tools",
                    "Credential",
                    "Last checked",
                    "Actions",
                  ].map((t) => (
                    <th key={t}>{t}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {((state.data as Server[]) || []).map((s) => (
                  <tr key={s.id}>
                    <td>
                      <strong>{s.display_name}</strong>
                      <small className="mono">{s.slug}</small>
                    </td>
                    <td>
                      <Status
                        value={!s.enabled ? "disabled" : s.observed_status}
                      />
                    </td>
                    <td>
                      <span className="endpoint mono" title={s.url}>
                        {s.url}
                      </span>
                    </td>
                    <td>
                      <Tools tools={s.tools} stale={s.tools_stale} />
                    </td>
                    <td>{s.has_credential ? "Configured" : "None"}</td>
                    <td className="mono timestamp">{time(s.last_checked)}</td>
                    <td>
                      <details className="actions">
                        <summary aria-label={"Actions for " + s.display_name}>
                          •••
                        </summary>
                        <div>
                          <button onClick={() => setEdit(s)}>Edit</button>
                          <button
                            disabled={!!busy || !s.enabled}
                            onClick={() => void action(s, "refresh")}
                          >
                            Refresh
                          </button>
                          <button
                            disabled={!!busy}
                            onClick={() =>
                              void action(s, s.enabled ? "disable" : "enable")
                            }
                          >
                            {s.enabled ? "Disable" : "Enable"}
                          </button>
                          <button
                            className="danger"
                            onClick={() => setConfirm(s)}
                          >
                            Remove
                          </button>
                        </div>
                      </details>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!(state.data as Server[])?.length && (
              <Empty>
                No servers registered yet. Add an upstream to get started.
              </Empty>
            )}
          </div>
        ) : (
          <section className="panel">
            <Tools tools={(state.data as { tools: Tool[] })?.tools || []} />
            {!(state.data as { tools: Tool[] })?.tools.length && (
              <Empty>
                No tools are currently available. Ask your administrator to
                check connections.
              </Empty>
            )}
          </section>
        )}
      </Load>
      <p className="footnote">
        Disabled servers are excluded from live gateway discovery. Cached tools
        are reference metadata only.
      </p>
      {edit !== undefined && (
        <ServerForm
          server={edit || undefined}
          onClose={() => setEdit(undefined)}
          onSave={() => {
            setEdit(undefined);
            state.reload();
          }}
        />
      )}
      {confirm && (
        <Confirm
          title="Remove server?"
          description={
            "Remove " +
            confirm.display_name +
            " and its connection configuration? Existing audit history is retained."
          }
          onCancel={() => setConfirm(null)}
          onConfirm={async () => {
            await api("/servers/" + confirm.id, undefined, "DELETE");
            setConfirm(null);
            state.reload();
          }}
        />
      )}
    </>
  );
}
function KeysTable({
  items,
  onRevoke,
}: {
  items: Key[];
  onRevoke: (k: Key) => void;
}) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {[
              "Name",
              "Prefix",
              "Created",
              "Last used",
              "Status",
              "Actions",
            ].map((t) => (
              <th key={t}>{t}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((k) => (
            <tr key={k.id}>
              <td>
                <strong>{k.label}</strong>
              </td>
              <td>
                <code>{k.prefix}</code>
              </td>
              <td className="mono timestamp">{time(k.created_at)}</td>
              <td className="mono timestamp">{time(k.last_used_at)}</td>
              <td>
                <Status value={k.revoked_at ? "revoked" : "active"} />
              </td>
              <td>
                <button
                  className="danger"
                  disabled={!!k.revoked_at}
                  onClick={() => onRevoke(k)}
                >
                  Revoke
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {!items.length && <Empty>You haven't created an API key yet.</Empty>}
    </div>
  );
}
export function Keys() {
  const state = useLoad<Key[]>("/keys");
  const [create, setCreate] = useState(false),
    [label, setLabel] = useState(""),
    [secret, setSecret] = useState(""),
    [revoke, setRevoke] = useState<Key | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  return (
    <>
      <Header
        title="API Keys"
        description="Connect external MCP clients with your own revocable gateway key."
        action={
          <button
            className="primary"
            onClick={() => {
              setCreate(true);
              setError("");
            }}
          >
            Create API key
          </button>
        }
      />
      <div className="connection-strip">
        <span>Gateway endpoint</span>
        <code>{location.origin}/mcp</code>
        <span className="muted">Bearer authentication</span>
      </div>
      <Load state={state}>
        <KeysTable items={state.data || []} onRevoke={setRevoke} />
      </Load>
      {create && (
        <Modal
          title="Create API key"
          onClose={() => {
            if (!busy) setCreate(false);
          }}
        >
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              setBusy(true);
              try {
                const r = await api<{ raw_key: string }>("/keys", { label });
                setSecret(r.raw_key);
                setCreate(false);
                setLabel("");
                state.reload();
              } catch {
                setError(
                  "Key creation failed. Inspect the key list before trying again.",
                );
              } finally {
                setBusy(false);
              }
            }}
          >
            <label>
              Key name
              <input
                required
                maxLength={100}
                value={label}
                placeholder="My external MCP client"
                onChange={(e) => setLabel(e.target.value)}
              />
            </label>
            {error && (
              <p role="alert" className="error">
                {error}
              </p>
            )}
            <div className="form-actions">
              <button className="primary" disabled={busy}>
                Create key
              </button>
            </div>
          </form>
        </Modal>
      )}
      {secret && (
        <Secret
          title="API key created"
          value={secret}
          onClose={() => setSecret("")}
        />
      )}
      {revoke && (
        <Confirm
          title="Revoke API key?"
          description={
            "Clients using " +
            revoke.label +
            " will be rejected on their next request."
          }
          onCancel={() => setRevoke(null)}
          onConfirm={async () => {
            await api("/keys/" + revoke.id, undefined, "DELETE");
            setRevoke(null);
            state.reload();
          }}
        />
      )}
    </>
  );
}
export function Team() {
  const state = useLoad<User[]>("/users");
  const [invite, setInvite] = useState(false),
    [username, setUsername] = useState(""),
    [secret, setSecret] = useState(""),
    [selected, setSelected] = useState<User | null>(null),
    [keys, setKeys] = useState<Key[]>([]),
    [revoke, setRevoke] = useState<Key | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  return (
    <>
      <Header
        title="Team"
        description="Invite members and manage their access to the shared gateway."
        action={
          <button
            className="primary"
            onClick={() => {
              setInvite(true);
              setError("");
            }}
          >
            Invite member
          </button>
        }
      />
      {error && !invite && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <Load state={state}>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                {["User", "Role", "Status", "API Keys"].map((t) => (
                  <th key={t}>{t}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {state.data?.map((u) => (
                <tr key={u.id}>
                  <td>
                    <strong>{u.username}</strong>
                    <small className="mono">{u.id}</small>
                  </td>
                  <td>
                    <span className="role">{u.role}</span>
                  </td>
                  <td>
                    <Status value={u.enabled ? "active" : "disabled"} />
                  </td>
                  <td>
                    <button
                      disabled={busy}
                      onClick={async () => {
                        setBusy(true);
                        try {
                          setKeys(await api<Key[]>("/users/" + u.id + "/keys"));
                          setSelected(u);
                        } catch {
                          setError("Unable to load member keys.");
                        } finally {
                          setBusy(false);
                        }
                      }}
                    >
                      View keys
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Load>
      {invite && (
        <Modal
          title="Invite member"
          onClose={() => {
            if (!busy) setInvite(false);
          }}
        >
          <p>
            Creates an expiring, single-use invitation for a member account.
            Share the token securely.
          </p>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              setBusy(true);
              try {
                const r = await api<{ token: string }>("/invitations", {
                  username,
                });
                setSecret(r.token);
                setInvite(false);
                setUsername("");
              } catch {
                setError(
                  "Invitation could not be created. Check the username.",
                );
              } finally {
                setBusy(false);
              }
            }}
          >
            <label>
              Intended username
              <input
                required
                value={username}
                maxLength={64}
                onChange={(e) => setUsername(e.target.value)}
              />
            </label>
            {error && (
              <p role="alert" className="error">
                {error}
              </p>
            )}
            <div className="form-actions">
              <button className="primary" disabled={busy}>
                Create invitation
              </button>
            </div>
          </form>
        </Modal>
      )}
      {secret && (
        <Secret
          title="Invitation created"
          value={secret}
          onClose={() => setSecret("")}
        />
      )}
      {selected && !revoke && (
        <Modal
          title={selected.username + " · API keys"}
          onClose={() => setSelected(null)}
        >
          <KeysTable items={keys} onRevoke={setRevoke} />
        </Modal>
      )}
      {selected && revoke && (
        <Confirm
          title="Revoke member API key?"
          description={
            "Revoke " +
            revoke.label +
            " for " +
            selected.username +
            "? You cannot retrieve the raw key."
          }
          onCancel={() => setRevoke(null)}
          onConfirm={async () => {
            await api(
              "/users/" + selected.id + "/keys/" + revoke.id,
              undefined,
              "DELETE",
            );
            setKeys(await api<Key[]>("/users/" + selected.id + "/keys"));
            setRevoke(null);
          }}
        />
      )}
    </>
  );
}
export function Audits() {
  const [page, setPage] = useState(1),
    [outcome, setOutcome] = useState("");
  const state = useLoad<{ items: Audit[]; total: number; has_more: boolean }>(
    "/audits?page=" +
      page +
      "&per_page=20" +
      (outcome ? "&outcome=" + outcome : ""),
  );
  return (
    <>
      <Header
        title="Audit"
        description="Attributed tool activity across external clients and dashboard chat."
      />
      <div className="toolbar">
        <label>
          Outcome
          <select
            value={outcome}
            onChange={(e) => {
              setOutcome(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All outcomes</option>
            <option>succeeded</option>
            <option>failed</option>
            <option>started</option>
          </select>
        </label>
        <button onClick={state.reload}>Refresh</button>
      </div>
      <Load state={state}>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                {[
                  "Time",
                  "User",
                  "Server",
                  "Tool",
                  "Duration",
                  "Outcome",
                  "Error",
                ].map((t) => (
                  <th key={t}>{t}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {state.data?.items.map((a) => (
                <tr key={a.id}>
                  <td className="mono timestamp">{time(a.started_at)}</td>
                  <td>{a.username}</td>
                  <td>
                    <code>{a.server_slug || "—"}</code>
                  </td>
                  <td>
                    <code className="wrap-code">{a.gateway_tool}</code>
                  </td>
                  <td className="mono">
                    {a.duration_ms === null ? "—" : a.duration_ms + " ms"}
                  </td>
                  <td>
                    <Status value={a.outcome} />
                  </td>
                  <td>
                    <code>{a.error_code || "—"}</code>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!state.data?.items.length && (
            <Empty>No tool calls recorded yet.</Empty>
          )}
        </div>
      </Load>
      <div className="pagination">
        <span>
          {state.data?.total || 0} events · Page {page}
        </span>
        <button
          disabled={page === 1 || state.loading}
          onClick={() => setPage((p) => p - 1)}
        >
          Previous
        </button>
        <button
          disabled={!state.data?.has_more || state.loading}
          onClick={() => setPage((p) => p + 1)}
        >
          Next
        </button>
      </div>
      <p className="footnote">
        Started events may indicate interrupted execution with an unknown
        outcome. Arguments and results are not stored here.
      </p>
    </>
  );
}
const chatErrors: Record<string, string> = {
  CHAT_NOT_CONFIGURED:
    "Chat is not configured yet. Ask your administrator to configure the model provider.",
  CHAT_TOOL_FAILED:
    "A tool did not complete successfully. No automatic retry was made. A write may have an unknown outcome; inspect its current state before trying again.",
  CHAT_ROUND_LIMIT:
    "The tool-round limit was reached. Review the activity before continuing.",
  PROVIDER_RATE_LIMIT: "The model provider is temporarily rate limited.",
  PROVIDER_AUTH_FAILED:
    "The model provider configuration needs administrator attention.",
};
export function Chat() {
  const [message, setMessage] = useState(""),
    [turns, setTurns] = useState<{ message: string; reply: Answer }[]>([]),
    [busy, setBusy] = useState(false);
  async function send() {
    if (busy || !message.trim()) return;
    const text = message.trim();
    setBusy(true);
    setMessage("");
    try {
      const reply = await api<Answer>("/chat", { message: text });
      setTurns((t) => [...t, { message: text, reply }]);
    } catch {
      setTurns((t) => [
        ...t,
        {
          message: text,
          reply: { answer: "", trace: [], error: "REQUEST_FAILED" },
        },
      ]);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Header
        title="Chat"
        description="Ask questions and take action across your connected tools."
        action={
          <button disabled={busy || !turns.length} onClick={() => setTurns([])}>
            Clear conversation
          </button>
        }
      />
      <section className="chat-console">
        <div className="conversation" aria-live="polite">
          {!turns.length && (
            <div className="chat-empty">
              <div className="eyebrow">YOUR TOOLS, WORKING TOGETHER</div>
              <h2>What would you like to work on?</h2>
              <p>
                Ask about orders, compare totals, or look up handling policies.
              </p>
              <div className="starters">
                {[
                  "What orders came in today?",
                  "What are today’s total and average order values?",
                  "For today’s COD orders, what handling policy applies?",
                ].map((s) => (
                  <button key={s} onClick={() => setMessage(s)}>
                    {s}
                    <span aria-hidden="true">↗</span>
                  </button>
                ))}
              </div>
            </div>
          )}
          {turns.map((t, i) => (
            <article className="chat-turn" key={i}>
              <div className="chat-user">
                <small className="eyebrow">YOU</small>
                <p>{t.message}</p>
              </div>
              <div className="chat-answer">
                <small className="eyebrow">URUMI</small>
                {t.reply.answer && (
                  <p className="answer-text">{t.reply.answer}</p>
                )}
                {t.reply.error && (
                  <p role="alert" className="error">
                    {chatErrors[t.reply.error] ||
                      "The request could not finish. Review any tool activity before submitting again; a write may already have taken effect."}
                  </p>
                )}
                {!!t.reply.trace.length && (
                  <section className="tool-activity" aria-label="Tool activity">
                    <header>
                      Tool activity <span>{t.reply.trace.length} calls</span>
                    </header>
                    {t.reply.trace.map((tr, j) => (
                      <div className="trace-row" key={j}>
                        <Status value={tr.outcome} />
                        <div>
                          <code>{tr.tool}</code>
                          <small>{tr.summary}</small>
                        </div>
                        <span className="mono">{tr.duration_ms} ms</span>
                      </div>
                    ))}
                  </section>
                )}
              </div>
            </article>
          ))}
          {busy && (
            <p className="thinking" role="status">
              Working through your tools…
            </p>
          )}
        </div>
        <form
          className="composer"
          onSubmit={(e) => {
            e.preventDefault();
            void send();
          }}
        >
          <label className="sr-only" htmlFor="prompt">
            Message
          </label>
          <textarea
            id="prompt"
            rows={2}
            maxLength={4000}
            value={message}
            disabled={busy}
            placeholder="Ask about orders, products, policies…"
            onChange={(e) => setMessage(e.target.value)}
          />
          <button className="primary" disabled={busy || !message.trim()}>
            {busy ? "Working…" : "Send"}
          </button>
          <small>
            Each message is independent. Tool calls are attributed to you and
            audited. Requested changes can modify store data.
          </small>
        </form>
      </section>
    </>
  );
}
