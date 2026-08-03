# Adaptive Learning Tutor MVP

A pnpm/Turborepo monorepo for an adaptive Algebra Foundations tutor. The core loop is curriculum graph → diagnostic assessment → deterministic mastery update → explainable next-best-action recommendation → curriculum-grounded tutor support.

## Architecture

- `apps/web`: Next.js, React, Tailwind UI reading `NEXT_PUBLIC_API_URL`.
- `apps/api`: Fastify + Prisma API for curriculum, mastery, recommendations, assessment, tutor, and graph validation.
- `apps/worker`: BullMQ worker for `GENERATE_RECOMMENDATION`, `RECALCULATE_MASTERY`, and `SUMMARIZE_TUTOR_SESSION`; logs a synchronous fallback without Redis.
- `packages/*`: shared types, graph traversal, assessment mastery, orchestration, and tutor provider abstraction.

## Local setup

```bash
pnpm install
docker compose up -d
cp .env.example .env
pnpm db:generate
pnpm db:migrate
pnpm db:seed
pnpm dev
```

Web runs on `http://localhost:3000`; API runs on `http://localhost:4000`.

## Environment variables

See `.env.example`: `DATABASE_URL`, `REDIS_URL`, `NEXT_PUBLIC_API_URL`, `API_PORT`, `NODE_ENV`, `AI_PROVIDER`, `AI_API_KEY`, `AI_MODEL`, `SESSION_SECRET`. The default tutor provider is `mock`, so no AI secret is required.

## Demo users

Seeded demo accounts are `admin@example.com`, `teacher@example.com`, and `learner@example.com`. Authentication is intentionally demo-only for MVP speed.

## Commands

- `pnpm test`
- `pnpm typecheck`
- `pnpm lint`
- `pnpm build`
- `pnpm db:seed`

## Railway summary

Connect the GitHub monorepo to Railway and create services for web, api, worker, postgres, and redis. See `docs/RAILWAY_DEPLOYMENT.md` for root directories, build/start commands, variables, migration, and seed instructions.

## Learning Object Registry and Runtime Container

A new capability is being built alongside the MVP: a registry and sandboxed
runtime container that launches independently-built edtech tools by URL via
LTI 1.3, renders them in an isolated iframe with a typed `postMessage`
bridge, and captures learner events as pseudonymised xAPI statements. It
will live in new `apps/registry-api`, `apps/launch-gateway`,
`apps/container-ui`, `apps/xapi-gateway`, and `packages/manifest-schema`,
`packages/lti-core`, `packages/bridge-protocol` workspaces, built out in
phases. See `docs/adr/` for the foundational architecture decisions
(launch protocol, iframe/cookie strategy, xAPI actor pseudonymisation).

## Limitations

MVP auth is seeded/demo only, graph storage uses PostgreSQL node/edge tables, recommendations are deterministic rules, and the default tutor is a structured mock provider.
