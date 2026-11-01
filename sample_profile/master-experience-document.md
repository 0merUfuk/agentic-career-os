# Master Experience Document (Sample)

The permanent knowledge base for the candidate. This document acts as the single source of truth for resume drafting, cover letters, and interview preparation.

---

## 0. Candidate Summary & Positioning

- **Name:** Alex Vance
- **Location:** San Francisco, CA (Open to Global Remote)
- **Role Focus:** AI Systems Engineering, Multi-Agent Platforms, Distributed Systems
- **Core Thesis:** *"AI proposes, deterministic code validates and gates, nothing with a real external effect happens without a hard policy check or human approval — fail closed on uncertainty, never fail open."*

---

## 1. Verified Production Experience

### Principal AI Infrastructure Engineer &bull; Synthetix Labs (2024 &ndash; Present)
- Architected multi-agent orchestration platform across 25+ production workflows serving enterprise workloads with automated multi-provider failover.
- Designed and implemented deterministic policy gates that validate model outputs before any external tool execution, ensuring fail-closed safety on uncertainty.
- Built Space Copilot, an advisory LLM-judge service evaluating production AI responses; redesigned its scoring metrics and resolved prompt-injection vulnerabilities.
- Built Mercury planner, turning natural language intent into codebase-grounded task trees bounded by strict verification gates before modifying central issue trackers.
- Led technical partnership evaluations and infrastructure integrations across leading foundation model inference providers.

### Senior Platform Engineer &bull; CloudMatrix Systems (2022 &ndash; 2024)
- Extracted 4 Go microservices from a legacy monolith with per-endpoint rollback safety and zero service disruption.
- Re-architected execution pipelines from synchronous HTTP blocking into an asynchronous queue-based job architecture with RabbitMQ and Redis, cutting latency from 60s to <100ms.
- Implemented automated payment and subscription infrastructure backed by 500+ unit and integration tests at 92%+ coverage behind a 5-stage CI/CD pipeline.
- Designed declarative pipeline orchestration reducing developer overhead for deploying new generation workflows by over 70%.
- Engineered multi-provider circuit breakers with priority-ordered fallback chains across external AI APIs.

### Distributed Systems Engineer &bull; DataCore Networks (2020 &ndash; 2022)
- Designed high-throughput network data ingestion and telemetry pipelines processing millions of events daily.
- Optimized PostgreSQL database schemas and implemented multi-tier caching with Redis for measurable latency reductions.
- Maintained Docker-based infrastructure and automated testing pipelines for core platform microservices.

---

## 2. Open Source & Key Projects

- **agent-gatekeeper**: Deterministic policy engine for LLM function calling (Go/Python, MIT License).
- **heimdall-cli**: Real-time meeting transcription and structured note synthesis CLI in Go with streaming LLM analysis.

---

## 3. Core Competencies

- **Languages:** Go, Python, TypeScript, Node.js, SQL, C++, Bash
- **AI & Agent Tooling:** Model Context Protocol (MCP), Claude Code, OpenAI Function Calling, Agent Governance, RAG, Prompt Injection Guards
- **Infrastructure:** Docker, Kubernetes, PostgreSQL, Redis, RabbitMQ, Microservices, CI/CD, Distributed Systems, Linux
