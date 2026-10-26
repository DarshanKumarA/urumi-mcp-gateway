import {
  render,
  screen,
  waitFor,
  within,
  fireEvent,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import { Servers, Keys, Team, Audits, Chat } from "./pages";
import { Secret, Status } from "./components";
import { api } from "./api";
const admin = {
  id: "a",
  username: "fixture_admin",
  role: "admin",
  enabled: true,
};
const member = {
  id: "b",
  username: "fixture_member",
  role: "member",
  enabled: true,
};
const server = {
  id: "s",
  slug: "woocommerce",
  display_name: "WooCommerce",
  url: "http://fixture.internal:8000/mcp",
  enabled: true,
  observed_status: "connected",
  has_credential: true,
  last_checked: null,
  tools: [{ name: "woocommerce__list_orders" }],
  tools_stale: false,
};
const key = {
  id: "k",
  label: "Fixture key",
  prefix: "fixture-prefix",
  created_at: "2026-10-25T00:00:00Z",
  last_used_at: null,
  revoked_at: null,
};
function mock(handler: (path: string, init: RequestInit) => unknown) {
  const fn = vi.fn(async (input: string, init: RequestInit = {}) => {
    const result = handler(input, init);
    return {
      ok: !(result as { status?: number })?.status,
      status: (result as { status?: number })?.status || 200,
      json: async () => result,
    };
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}
beforeEach(() => {
  history.replaceState(null, "", "/chat");
});
it("loads login then me and signs out", async () => {
  let logged = false;
  mock((p) => {
    if (p === "/api/auth/login") {
      logged = true;
      return admin;
    }
    if (p === "/api/auth/logout") {
      logged = false;
      return {};
    }
    return logged ? admin : { status: 401 };
  });
  render(<App />);
  await screen.findByRole("button", { name: "Sign in" });
  await userEvent.type(screen.getByLabelText("Username"), "fixture_admin");
  await userEvent.type(
    screen.getByLabelText("Password"),
    "synthetic-password-only",
  );
  await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
  await screen.findByRole("heading", { name: "Chat" });
  await userEvent.click(screen.getByRole("button", { name: "Sign out" }));
  await screen.findByRole("button", { name: "Sign in" });
});
it("admin navigation has all five pages", async () => {
  mock(() => admin);
  render(<App />);
  await screen.findByRole("navigation");
  for (const name of ["Chat", "Servers", "Team", "API Keys", "Audit"])
    expect(
      within(screen.getByRole("navigation")).getByText(name),
    ).toBeVisible();
});
it("member navigation excludes Team and Audit", async () => {
  mock(() => member);
  render(<App />);
  await screen.findByRole("navigation");
  expect(within(screen.getByRole("navigation")).queryByText("Team")).toBeNull();
  expect(
    within(screen.getByRole("navigation")).queryByText("Audit"),
  ).toBeNull();
});
it("renders all three server states and readable tools", async () => {
  mock(() => [
    server,
    {
      ...server,
      id: "b",
      display_name: "Down",
      observed_status: "unreachable",
    },
    { ...server, id: "c", display_name: "Off", enabled: false },
  ]);
  render(<Servers admin />);
  await screen.findByText("Connected");
  expect(screen.getByText("Unreachable")).toBeVisible();
  expect(screen.getByText("Disabled")).toBeVisible();
  expect(screen.getAllByText("1 tools")).toHaveLength(3);
});
it("disable sends exactly one action", async () => {
  const f = mock(() => [server]);
  render(<Servers admin />);
  await screen.findByText("WooCommerce");
  await userEvent.click(screen.getByLabelText("Actions for WooCommerce"));
  await userEvent.click(screen.getByRole("button", { name: "Disable" }));
  await waitFor(() =>
    expect(f.mock.calls.filter(([p]) => p.endsWith("/disable"))).toHaveLength(
      1,
    ),
  );
});
it("member catalog hides administration", async () => {
  mock(() => ({ tools: [{ name: "woocommerce__list_orders" }] }));
  render(<Servers admin={false} />);
  await screen.findByText("1 tools");
  expect(screen.queryByRole("button", { name: "Add server" })).toBeNull();
});
it("normal edit omits credential and preserves immutable slug", async () => {
  const f = mock(() => [server]);
  render(<Servers admin />);
  await screen.findByText("WooCommerce");
  await userEvent.click(screen.getByLabelText("Actions for WooCommerce"));
  await userEvent.click(screen.getByRole("button", { name: "Edit" }));
  expect(screen.getByLabelText(/Server slug/)).toBeDisabled();
  await userEvent.click(screen.getByRole("button", { name: "Save server" }));
  await waitFor(() =>
    expect(f.mock.calls.find(([, i]) => i?.method === "PATCH")).toBeTruthy(),
  );
  const body = JSON.parse(
    f.mock.calls.find(([, i]) => i?.method === "PATCH")![1]?.body as string,
  );
  expect(body).not.toHaveProperty("credential");
  expect(body).not.toHaveProperty("slug");
});
it("server removal requires confirmation", async () => {
  const f = mock(() => [server]);
  render(<Servers admin />);
  await screen.findByText("WooCommerce");
  await userEvent.click(screen.getByLabelText("Actions for WooCommerce"));
  await userEvent.click(screen.getByRole("button", { name: "Remove" }));
  expect(f.mock.calls.some(([, i]) => i?.method === "DELETE")).toBe(false);
  await userEvent.click(screen.getByRole("button", { name: "Confirm" }));
  await waitFor(() =>
    expect(f.mock.calls.some(([, i]) => i?.method === "DELETE")).toBe(true),
  );
});
it("invitation is shown once and cleared after dismissal", async () => {
  mock((p) =>
    p === "/api/users"
      ? [admin, member]
      : { token: "synthetic-invitation-only" },
  );
  render(<Team />);
  await userEvent.click(screen.getByRole("button", { name: "Invite member" }));
  await userEvent.type(screen.getByLabelText("Intended username"), "member_b");
  await userEvent.click(
    screen.getByRole("button", { name: "Create invitation" }),
  );
  await screen.findByDisplayValue("synthetic-invitation-only");
  await userEvent.click(screen.getByRole("button", { name: "Done" }));
  expect(screen.queryByDisplayValue("synthetic-invitation-only")).toBeNull();
});
it("API key is shown once and disappears on dismissal", async () => {
  mock((p, i) =>
    i?.method === "POST" ? { raw_key: "synthetic-key-only" } : [],
  );
  render(<Keys />);
  await userEvent.click(screen.getByRole("button", { name: "Create API key" }));
  await userEvent.type(screen.getByLabelText("Key name"), "fixture");
  await userEvent.click(screen.getByRole("button", { name: "Create key" }));
  await screen.findByDisplayValue("synthetic-key-only");
  await userEvent.click(screen.getByRole("button", { name: "Done" }));
  expect(screen.queryByDisplayValue("synthetic-key-only")).toBeNull();
});
it("key revocation requires confirmation", async () => {
  const f = mock(() => [key]);
  render(<Keys />);
  await screen.findByText("Fixture key");
  await userEvent.click(screen.getByRole("button", { name: "Revoke" }));
  expect(f.mock.calls.some(([, i]) => i?.method === "DELETE")).toBe(false);
  await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
  expect(screen.queryByRole("dialog")).toBeNull();
});
it("admin views and revokes member key without seeing raw key", async () => {
  const f = mock((p) => (p === "/api/users" ? [member] : [key]));
  render(<Team />);
  await screen.findByText("fixture_member");
  await userEvent.click(screen.getByRole("button", { name: "View keys" }));
  await screen.findByText("Fixture key");
  await userEvent.click(screen.getByRole("button", { name: "Revoke" }));
  await userEvent.click(screen.getByRole("button", { name: "Confirm" }));
  await waitFor(() =>
    expect(
      f.mock.calls.some(
        ([p, i]) => p === "/api/users/b/keys/k" && i?.method === "DELETE",
      ),
    ).toBe(true),
  );
});
it("audit renders attributed metadata and bounded pagination", async () => {
  mock(() => ({
    items: [
      {
        id: "e",
        username: "fixture_member",
        server_slug: "arithmetic",
        gateway_tool: "arithmetic__sum_amounts",
        started_at: "2026-10-25T00:00:00Z",
        duration_ms: 12,
        outcome: "succeeded",
        error_code: null,
      },
    ],
    total: 1,
    has_more: false,
  }));
  render(<Audits />);
  await screen.findByText("arithmetic__sum_amounts");
  expect(screen.getByText("Succeeded")).toBeVisible();
  expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
});
it("chat renders answer with two-server trace", async () => {
  const f = mock(() => ({
    answer: "Total 499, average 499",
    error: null,
    trace: [
      {
        tool: "woocommerce__list_orders",
        server: "woocommerce",
        outcome: "succeeded",
        duration_ms: 84,
        summary: "Tool completed.",
      },
      {
        tool: "arithmetic__sum_amounts",
        server: "arithmetic",
        outcome: "succeeded",
        duration_ms: 4,
        summary: "Tool completed.",
      },
    ],
  }));
  render(<Chat />);
  await userEvent.type(screen.getByLabelText("Message"), "Today totals");
  await userEvent.click(screen.getByRole("button", { name: "Send" }));
  await screen.findByText("Total 499, average 499");
  expect(screen.getByLabelText("Tool activity")).toBeVisible();
  expect(screen.getByText("arithmetic__sum_amounts")).toBeVisible();
  expect(f).toHaveBeenCalledTimes(1);
});
it("chat does not retry a failed mutation", async () => {
  const f = mock(() => ({
    answer: "",
    error: "CHAT_TOOL_FAILED",
    trace: [
      {
        tool: "woocommerce__create_product",
        server: "woocommerce",
        outcome: "failed",
        duration_ms: 10,
        summary: "Tool failed; no automatic retry.",
      },
    ],
  }));
  render(<Chat />);
  await userEvent.type(screen.getByLabelText("Message"), "Create fixture");
  await userEvent.click(screen.getByRole("button", { name: "Send" }));
  await screen.findByRole("alert");
  expect(f).toHaveBeenCalledTimes(1);
  expect(screen.getByRole("alert")).toHaveTextContent("unknown outcome");
});
it("chat empty starters set input only", async () => {
  const f = mock(() => ({}));
  render(<Chat />);
  await userEvent.click(
    screen.getByRole("button", { name: /What orders came in today/ }),
  );
  expect(screen.getByLabelText("Message")).toHaveValue(
    "What orders came in today?",
  );
  expect(f).not.toHaveBeenCalled();
});
it("loading state is explicit", () => {
  vi.stubGlobal("fetch", () => new Promise(() => {}));
  render(<Keys />);
  expect(screen.getByRole("status")).toHaveTextContent("Loading");
});
it("empty key state", async () => {
  mock(() => []);
  render(<Keys />);
  await screen.findByText("You haven't created an API key yet.");
});
it("empty audit state", async () => {
  mock(() => ({ items: [], total: 0, has_more: false }));
  render(<Audits />);
  await screen.findByText("No tool calls recorded yet.");
});
it("safe error never shows raw response", async () => {
  mock(() => ({ status: 500, secret: "never-display-fixture" }));
  render(<Servers admin />);
  await screen.findByRole("alert");
  expect(screen.queryByText("never-display-fixture")).toBeNull();
  expect(screen.getByRole("button", { name: "Retry" })).toBeVisible();
});
it("invitation acceptance uses token in body not URL", async () => {
  history.replaceState(null, "", "/accept-invitation");
  const f = mock((p) => (p === "/api/me" ? { status: 401 } : {}));
  render(<App />);
  await screen.findByLabelText("Invitation token");
  await userEvent.type(
    screen.getByLabelText("Invitation token"),
    "synthetic-invite",
  );
  await userEvent.type(
    screen.getByLabelText("Password"),
    "synthetic-password-only",
  );
  await userEvent.click(screen.getByRole("button", { name: "Create account" }));
  await screen.findByText("Account created. Sign in to continue.");
  expect(f.mock.calls.some(([p]) => p.includes("synthetic-invite"))).toBe(
    false,
  );
});
it("relative API requests always include cookies", async () => {
  const f = mock(() => ({}));
  await api("/keys");
  expect(f).toHaveBeenCalledWith(
    "/api/keys",
    expect.objectContaining({ credentials: "include" }),
  );
});
it("secret dialog escapes text and supports Escape dismissal", async () => {
  const close = vi.fn();
  render(
    <Secret title="Fixture" value="<script>fixture</script>" onClose={close} />,
  );
  expect(document.querySelector("script")).toBeNull();
  fireEvent(screen.getByRole("dialog"), new Event("cancel", { bubbles: true }));
  expect(close).toHaveBeenCalled();
});
it("statuses include text and do not rely on color", () => {
  render(<Status value="disabled" />);
  expect(screen.getByText("Disabled")).toBeVisible();
});
