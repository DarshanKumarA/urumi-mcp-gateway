# MCP Gateway on Kubernetes

This repository is for the Urumi AI FDE internship assignment: run a WooCommerce store on Kubernetes, write its MCP server, aggregate at least three upstream MCP servers through a team gateway, and provide a React dashboard with a chat agent that uses the gateway as the logged-in user.

**Current state:** governance documentation drafted for review. No application, deployment, or runnable setup exists. No runtime requirement or live demo has been implemented or verified.

## Source of truth and project documents

The [original assignment DOCX](docs/source/urumi-mcp-gateway-assignment.docx) is authoritative. The [faithful Markdown transcription](docs/assignment.md) preserves its mandatory requirements, optional work, live demonstrations, deliverables, and evaluation expectations. Proposals elsewhere do not change the assignment.

| File | Purpose |
| --- | --- |
| [AGENTS.md](AGENTS.md) | Required learning, planning, change, review, and validation process |
| [.gitignore](.gitignore) | Exclude generated output and recognizable local secret files |
| [docs/requirements.md](docs/requirements.md) | Stable requirement IDs, verification plans, demo mapping, and optional scope |
| [docs/architecture.md](docs/architecture.md) | Assignment constraints, proposed design, and open decisions |
| [docs/decisions.md](docs/decisions.md) | Accepted governance choices and proposed engineering choices with rationale |
| [docs/progress.md](docs/progress.md) | Milestone status, validation evidence, and review boundary |
| [docs/threat-model.md](docs/threat-model.md) | Required threat analysis, required controls, and separate optional hardening |

## Proposed technology baseline

React is required for the dashboard. The assignment also mandates WordPress with WooCommerce, Kubernetes, Helm (not Kustomize), Streamable HTTP for the custom WooCommerce MCP server and supported upstreams, and Kubernetes Secrets.

Vite, Python, FastAPI, the official Python MCP SDK, Python for the upstream servers, PostgreSQL for gateway/control-plane state, MariaDB for the store, Docker, Minikube with the Docker driver, and k3s for the production-like target remain **proposed**. Specific versions, packages, and deployment layouts are not selected. The model/provider is also undecided. See the [architecture](docs/architecture.md) for choices and alternatives.

The mandatory core uses one store. Multi-store provisioning and other stand-out work are optional and have not been selected. VPS deployability using the same Helm charts and configuration changes is mandatory; actually demonstrating a VPS deployment is listed as stand-out work.

## Setup and use instructions status

The assignment requires this README eventually to include local setup, VPS/production-like setup, ordering on the storefront, external MCP client connection, and chat usage instructions. Those instructions are pending implementation and validation; there are no commands to run yet. Their acceptance criteria are tracked as REQ-DEL-01 in [requirements](docs/requirements.md).

## Working process

Understand → plan → identify files → implement small change → review diff → validate → document → verify understanding. Follow [AGENTS.md](AGENTS.md), keep changes small, and stop at major milestones. Real credentials must never enter source code or committed configuration. The current boundary is documentation review only, with no commit or application implementation authorized.
