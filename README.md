# MCP Gateway on Kubernetes

This repository is for the Urumi AI FDE internship assignment: run a WooCommerce store on Kubernetes, write its MCP server, aggregate at least three upstream MCP servers through a team gateway, and provide a React dashboard with a chat agent that uses the gateway as the logged-in user.

**Current state:** Stage 0 governance and Architecture v1 are approved and committed as 51f27b2 and db49836 on main. Stage 2 environment preflight has been reviewed, and k3d is selected for local Kubernetes. Toolchain installation and cluster creation remain pending. No application, deployment, or runnable setup exists. No runtime requirement or live demo has been implemented or verified.

## Source of truth and project documents

The [original assignment DOCX](docs/source/urumi-mcp-gateway-assignment.docx) is authoritative. The [faithful Markdown transcription](docs/assignment.md) preserves its mandatory requirements, optional work, live demonstrations, deliverables, and evaluation expectations. Proposals elsewhere do not change the assignment.

| File | Purpose |
| --- | --- |
| [AGENTS.md](AGENTS.md) | Required learning, planning, change, review, and validation process |
| [.gitignore](.gitignore) | Exclude generated output and recognizable local secret files |
| [docs/requirements.md](docs/requirements.md) | Stable requirement IDs, verification plans, demo mapping, and optional scope |
| [docs/architecture.md](docs/architecture.md) | Assignment constraints, approved Architecture v1, and open implementation details |
| [docs/decisions.md](docs/decisions.md) | Individual decisions, alternatives, rationale, and explicitly superseded proposals |
| [docs/progress.md](docs/progress.md) | Milestone status, validation evidence, and review boundary |
| [docs/project-journey.md](docs/project-journey.md) | Chronological engineering story and learning for an interview walkthrough |
| [docs/threat-model.md](docs/threat-model.md) | Required threat analysis, required controls, and separate optional hardening |

## Technology decisions and proposals

React is required for the dashboard. The assignment also mandates WordPress with WooCommerce, Kubernetes, Helm (not Kustomize), Streamable HTTP for the custom WooCommerce MCP server and supported upstreams, and Kubernetes Secrets.

Architecture v1 accepts one Python/FastAPI backend, the official Python MCP SDK, PostgreSQL for gateway state, MariaDB for the store, one application namespace, and one application Helm chart/release. The additional upstreams are arithmetic and store policy/reference servers with no external service dependencies. These are implementation choices, not technologies mandated by the assignment.

k3d is the **selected** local cluster tool, with Docker Desktop as the intended container runtime, replacing the earlier Minikube proposal after environment preflight (DEC-017). This is a project choice; the assignment permits Kind, k3d, or Minikube. Vite and k3s for the production-like VPS remain **proposed**. The model/provider, exact versions, SDK connection lifecycle, runtime Secret management, and store/chart packaging remain open. Verify SDK/protocol compatibility at implementation time and pin exact package versions; moving defaults are not permanent contracts. See the [architecture](docs/architecture.md) for approved boundaries and remaining decisions.

The mandatory core uses one store. Multi-store provisioning and other stand-out work are optional and have not been selected. VPS deployability using the same Helm charts and configuration changes is mandatory; actually demonstrating a VPS deployment is listed as stand-out work.

## Setup and use instructions status

The assignment requires this README eventually to include local setup, VPS/production-like setup, ordering on the storefront, external MCP client connection, and chat usage instructions. Those instructions are pending implementation and validation; there are no commands to run yet. Their acceptance criteria are tracked as REQ-DEL-01 in [requirements](docs/requirements.md).

## Working process

Understand → plan → identify files → implement small change → review diff → validate → document → verify understanding. Follow [AGENTS.md](AGENTS.md), keep changes small, and stop at major milestones. Real credentials must never enter source code or committed configuration. The current authorization covers the k3d documentation checkpoint and its commit; installation, cluster creation, and application implementation require a later reviewed step.
