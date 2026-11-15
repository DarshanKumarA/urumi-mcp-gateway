import { render, screen, cleanup } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { AnswerContent } from "./AnswerContent";
afterEach(cleanup);
it("renders real headers, rows, emphasis and lists", () => {
  render(<AnswerContent text={'Orders\n\n| Order | Total |\n| --- | ---: |\n| 31 | INR 499 |\n\n- **Average:** INR 499'} />);
  expect(screen.getAllByRole("columnheader")).toHaveLength(2);
  expect(screen.getByRole("cell", { name: "31" })).toBeVisible();
  expect(screen.getByRole("listitem")).toHaveTextContent("Average: INR 499");
  expect(screen.getByText("Average:").tagName).toBe("STRONG");
});
it("does not execute model HTML or create remote images or links", () => {
  const { container } = render(<AnswerContent text={'<img src=x onerror=alert(1)>\n<script>alert(1)</script>\n[link](javascript:alert(1))\n![image](https://example.invalid/pixel)'} />);
  expect(container.querySelectorAll("script,img,a")).toHaveLength(0);
  expect(screen.getByText('<script>alert(1)</script>')).toBeVisible();
});
it("preserves escaped pipes and malformed rows as readable text", () => {
  render(<AnswerContent text={'| Item | Total |\n| --- | --- |\n| A\\|B | 2 |\n| incomplete |'} />);
  expect(screen.getByRole("cell", { name: "A|B" })).toBeVisible();
  expect(screen.getByText("| incomplete |")).toBeVisible();
});
