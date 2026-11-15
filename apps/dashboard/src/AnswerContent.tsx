import { type ReactNode } from "react";

// A deliberately small, text-only Markdown subset. No HTML, images, or active links.
function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*\n]+\*\*|`[^`\n]+`)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**") ? <strong key={i}>{part.slice(2, -2)}</strong>
      : part.startsWith("`") && part.endsWith("`") ? <code key={i}>{part.slice(1, -1)}</code>
        : part,
  );
}
function cells(line: string): string[] {
  return line.trim().replace(/^\|/, "").replace(/\|$/, "").split(/(?<!\\)\|/)
    .map(cell => cell.trim().replace(/\\\|/g, "|"));
}
function separator(line: string): boolean {
  return line.includes("|") && cells(line).every(cell => /^:?-{3,}:?$/.test(cell));
}
export function AnswerContent({ text }: { text: string }) {
  const lines = text.replace(/\r\n/g, "\n").split("\n");
  const blocks: ReactNode[] = [];
  for (let i = 0; i < lines.length;) {
    if (!lines[i].trim()) { i++; continue; }
    const start = i;
    if (lines[i].includes("|") && i + 1 < lines.length && separator(lines[i + 1])) {
      const headers = cells(lines[i]);
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && lines[i].includes("|") && cells(lines[i]).length === headers.length) rows.push(cells(lines[i++]));
      blocks.push(<div className="answer-table" key={start} role="region" aria-label="Answer table" tabIndex={0}>
        <table><thead><tr>{headers.map((h, n) => <th scope="col" key={n}>{inline(h)}</th>)}</tr></thead>
          <tbody>{rows.map((row, n) => <tr key={n}>{row.map((c, k) => <td key={k}>{inline(c)}</td>)}</tr>)}</tbody></table>
      </div>);
    } else if (/^\s*[-*] /.test(lines[i])) {
      const items: string[] = [];
      while (i < lines.length && /^\s*[-*] /.test(lines[i])) items.push(lines[i++].replace(/^\s*[-*] /, ""));
      blocks.push(<ul key={start}>{items.map((item, n) => <li key={n}>{inline(item)}</li>)}</ul>);
    } else if (/^#{1,6} /.test(lines[i])) {
      blocks.push(<h3 key={start}>{inline(lines[i++].replace(/^#{1,6} /, ""))}</h3>);
    } else {
      blocks.push(<p key={start}>{inline(lines[i++])}</p>);
    }
  }
  return <div className="answer-content">{blocks}</div>;
}
