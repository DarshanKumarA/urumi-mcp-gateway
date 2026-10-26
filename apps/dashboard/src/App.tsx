import { useEffect, useState } from "react";
import { api, type User } from "./api";
import { Servers, Team, Keys, Audits, Chat } from "./pages";

function Authentication({
  accepted,
  onLogin,
}: {
  accepted: boolean;
  onLogin: (user: User) => void;
}) {
  const [user, setUser] = useState(""),
    [password, setPassword] = useState(""),
    [token, setToken] = useState("");
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [done, setDone] = useState(false);
  return (
    <main className="auth-canvas">
      <section className="auth-panel">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">
            U
          </span>{" "}
          Urumi <span className="brand-muted">Gateway</span>
        </div>
        <div className="eyebrow">TEAM MCP WORKSPACE</div>
        <h1>
          {accepted && !done
            ? "Accept invitation"
            : "Sign in to your workspace"}
        </h1>
        <p className="muted">
          {accepted && !done
            ? "Create your member account with the invitation from your administrator."
            : "One workspace for your tools, team and agent activity."}
        </p>
        {done && (
          <p role="status" className="notice">
            Account created. Sign in to continue.
          </p>
        )}
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            if (busy) return;
            setBusy(true);
            setError("");
            try {
              if (accepted && !done) {
                await api("/invitations/accept", { token, password });
                setToken("");
                setPassword("");
                setDone(true);
              } else {
                await api("/auth/login", { username: user, password });
                setPassword("");
                onLogin(await api<User>("/me"));
              }
            } catch {
              setError(
                accepted && !done
                  ? "Invitation could not be accepted. Check the token and password."
                  : "Unable to sign in. Check your username and password.",
              );
              setPassword("");
            } finally {
              setBusy(false);
            }
          }}
        >
          {accepted && !done ? (
            <label>
              Invitation token
              <input
                required
                autoComplete="off"
                type="password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
              />
            </label>
          ) : (
            <label>
              Username
              <input
                required
                autoComplete="username"
                value={user}
                onChange={(e) => setUser(e.target.value)}
              />
            </label>
          )}
          <label>
            Password
            <input
              required
              minLength={accepted && !done ? 12 : 1}
              maxLength={128}
              type="password"
              autoComplete={
                accepted && !done ? "new-password" : "current-password"
              }
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          {accepted && !done && <small>Use at least 12 characters.</small>}
          {error && (
            <p role="alert" className="error">
              {error}
            </p>
          )}
          <button className="primary auth-submit" disabled={busy}>
            {busy
              ? "Please wait…"
              : accepted && !done
                ? "Create account"
                : "Sign in"}
          </button>
        </form>
        <a
          className="auth-link"
          href={accepted ? "/login" : "/accept-invitation"}
        >
          {accepted ? "Back to sign in" : "Have an invitation?"}
        </a>
        <footer>Credentials stay between you and your gateway.</footer>
      </section>
    </main>
  );
}
const titles: Record<string, string> = {
  chat: "Chat",
  servers: "Servers",
  team: "Team",
  keys: "API Keys",
  audit: "Audit",
};
export default function App() {
  const [user, setUser] = useState<User | null>(null),
    [loading, setLoading] = useState(true),
    [error, setError] = useState(false);
  const [page, setPage] = useState(location.pathname.slice(1) || "chat"),
    [logoutBusy, setLogoutBusy] = useState(false);
  async function load() {
    setLoading(true);
    setError(false);
    try {
      setUser(await api<User>("/me"));
    } catch (e) {
      if ((e as { status?: number }).status !== 401) setError(true);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void load();
    const expired = () => setUser(null);
    const pop = () => setPage(location.pathname.slice(1) || "chat");
    window.addEventListener("urumi:expired", expired);
    window.addEventListener("popstate", pop);
    return () => {
      window.removeEventListener("urumi:expired", expired);
      window.removeEventListener("popstate", pop);
    };
  }, []);
  if (loading)
    return (
      <main className="auth-canvas">
        <p role="status">Loading workspace…</p>
      </main>
    );
  if (error && !user)
    return (
      <main className="auth-canvas">
        <div className="auth-panel">
          <h1>Workspace unavailable</h1>
          <p>We could not connect to the gateway.</p>
          <button onClick={() => void load()}>Retry</button>
        </div>
      </main>
    );
  if (!user)
    return (
      <Authentication
        accepted={page === "accept-invitation"}
        onLogin={(u) => {
          setUser(u);
          setPage("chat");
          history.replaceState(null, "", "/chat");
        }}
      />
    );
  const allowed =
    user.role === "admin"
      ? ["chat", "servers", "team", "keys", "audit"]
      : ["chat", "servers", "keys"];
  const selected = allowed.includes(page) ? page : "chat";
  return (
    <div className="shell">
      <header className="topbar">
        <a
          className="brand"
          href="/chat"
          onClick={(e) => {
            e.preventDefault();
            setPage("chat");
            history.pushState(null, "", "/chat");
          }}
        >
          <span className="brand-mark" aria-hidden="true">
            U
          </span>{" "}
          Urumi <span className="brand-muted">Gateway</span>
        </a>
        <div className="account">
          <span>{user.username}</span>
          <span className="role">{user.role}</span>
          <button
            disabled={logoutBusy}
            onClick={async () => {
              setLogoutBusy(true);
              try {
                await api("/auth/logout", {}, "POST");
                setUser(null);
              } catch {
                setError(true);
              } finally {
                setLogoutBusy(false);
              }
            }}
          >
            Sign out
          </button>
        </div>
      </header>
      <aside className="sidebar">
        <div className="eyebrow">WORKSPACE</div>
        <nav aria-label="Main navigation">
          {allowed.map((key) => (
            <a
              href={"/" + key}
              key={key}
              aria-current={selected === key ? "page" : undefined}
              onClick={(e) => {
                e.preventDefault();
                setPage(key);
                history.pushState(null, "", "/" + key);
              }}
            >
              <span className="nav-glyph" aria-hidden="true">
                {
                  {
                    chat: "›_",
                    servers: "▤",
                    team: "◎",
                    keys: "⌘",
                    audit: "≡",
                  }[key]
                }
              </span>
              {titles[key]}
            </a>
          ))}
        </nav>
        <div className="sidebar-note">
          <span className="mono">/mcp</span>
          <p>
            One endpoint.
            <br />
            Your team's tools.
          </p>
        </div>
      </aside>
      <main className="workspace" id="main-content">
        {error && (
          <p role="alert" className="error">
            Sign out failed. Please try again.
          </p>
        )}
        <div key={selected}>
          {selected === "chat" ? (
            <Chat />
          ) : selected === "servers" ? (
            <Servers admin={user.role === "admin"} />
          ) : selected === "team" ? (
            <Team />
          ) : selected === "keys" ? (
            <Keys />
          ) : (
            <Audits />
          )}
        </div>
      </main>
    </div>
  );
}
