import { useEffect, useRef, useState, type ReactNode } from "react";
export function Status({ value }: { value: string }) {
  const label: Record<string, string> = {
    connected: "Connected",
    unreachable: "Unreachable",
    disabled: "Disabled",
    unknown: "Not checked",
    succeeded: "Succeeded",
    failed: "Failed",
    started: "Started / unknown",
    active: "Active",
    revoked: "Revoked",
  };
  return (
    <span className={"status " + value}>
      <span aria-hidden="true" className="status-dot" />
      {label[value] || value}
    </span>
  );
}
export function Header({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <header className="page-heading">
      <div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </header>
  );
}
export function Modal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const old = document.activeElement as HTMLElement;
    ref.current?.showModal();
    return () => old?.focus();
  }, []);
  return (
    <dialog
      ref={ref}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      aria-labelledby="modal-title"
    >
      <div className="dialog-heading">
        <h2 id="modal-title">{title}</h2>
        <button aria-label="Close dialog" onClick={onClose}>
          ×
        </button>
      </div>
      {children}
    </dialog>
  );
}
export function Secret({
  title,
  value,
  onClose,
}: {
  title: string;
  value: string;
  onClose: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState(false);
  return (
    <Modal title={title} onClose={onClose}>
      <p>Copy this now. You will not be able to view it again.</p>
      <textarea
        className="secret mono"
        readOnly
        aria-label="One-time value"
        value={value}
      />
      <p role="status">
        {copied
          ? "Copied to clipboard."
          : error
            ? "Select and copy the value manually."
            : "This value is shown only once."}
      </p>
      <div className="form-actions">
        <button
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(value);
              setCopied(true);
            } catch {
              setError(true);
            }
          }}
        >
          Copy
        </button>
        <button className="primary" onClick={onClose}>
          Done
        </button>
      </div>
    </Modal>
  );
}
export function Confirm({
  title,
  description,
  onCancel,
  onConfirm,
}: {
  title: string;
  description: string;
  onCancel: () => void;
  onConfirm: () => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  return (
    <Modal
      title={title}
      onClose={() => {
        if (!busy) onCancel();
      }}
    >
      <p>{description}</p>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <div className="form-actions">
        <button disabled={busy} onClick={onCancel}>
          Cancel
        </button>
        <button
          disabled={busy}
          className="danger"
          onClick={async () => {
            setBusy(true);
            try {
              await onConfirm();
            } catch {
              setError(
                "Action could not be completed. Check the current state before retrying.",
              );
              setBusy(false);
            }
          }}
        >
          {busy ? "Working…" : "Confirm"}
        </button>
      </div>
    </Modal>
  );
}
export function Empty({ children }: { children: ReactNode }) {
  return <div className="empty">{children}</div>;
}
export function Failure({ retry }: { retry: () => void }) {
  return (
    <div className="error" role="alert">
      Unable to load this view. <button onClick={retry}>Retry</button>
    </div>
  );
}
export function time(value: string | null) {
  return value ? new Date(value).toLocaleString() : "—";
}
