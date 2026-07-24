# Railway Deployment

Create a Railway project connected to the GitHub monorepo. Add services: `web`, `api`, `worker`, PostgreSQL, and Redis. Configure variables from `.env.example`; use Railway-provided `DATABASE_URL` and `REDIS_URL`.

Recommended settings (each service also has a checked-in `railway.json` in its app directory with matching `build.buildCommand` / `deploy.startCommand`):
- web root: `apps/web`; build: `pnpm install --frozen-lockfile && pnpm turbo run build --filter=web...`; start: `pnpm start --filter web`.
- api root: `apps/api`; build: `pnpm install --frozen-lockfile && pnpm db:generate && pnpm turbo run build --filter=api...`; start: `pnpm db:migrate && pnpm start --filter api`.
- worker root: `apps/worker`; build: `pnpm install --frozen-lockfile && pnpm turbo run build --filter=worker...`; start: `pnpm start --filter worker`.

Builds must go through `turbo run build --filter=<app>...` (not a bare `pnpm build --filter <app>`), because the `<app>...` suffix tells Turborepo to build the app's `packages/*` workspace dependencies first via the `dependsOn: ["^build"]` rule in `turbo.json`. Every internal package publishes through `dist/` (its `package.json` `main` field), so skipping that step leaves `dist/` missing and the service crashes on start with `Cannot find module '@tutor/...'`.

`pnpm install --frozen-lockfile` requires a committed `pnpm-lock.yaml` at the repo root that matches every `package.json` — regenerate and commit it (`pnpm install`) after any dependency or workspace-package-name change, or the install step fails immediately.

If Railway executes from the repository root, keep the commands exactly as above. After deployment, run `pnpm db:seed` once from the API service shell to create demo users and Algebra Foundations curriculum. If Redis is absent locally, worker behavior falls back synchronously for MVP jobs.
