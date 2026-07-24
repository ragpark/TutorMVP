# Railway Deployment

Create a Railway project connected to the GitHub monorepo. Add services: `web`, `api`, `worker`, PostgreSQL, and Redis. Configure variables from `.env.example`; use Railway-provided `DATABASE_URL` and `REDIS_URL`.

Recommended settings (each service also has a checked-in `railway.json` in its app directory with matching `build.buildCommand` / `deploy.startCommand`):
- web root: `apps/web`; build: `pnpm install --frozen-lockfile && pnpm turbo run build --filter=web...`; start: `pnpm start --filter web`.
- api root: `apps/api`; build: `pnpm install --frozen-lockfile && pnpm db:generate && pnpm turbo run build --filter=api...`; start: `pnpm db:migrate && pnpm start --filter api`.
- worker root: `apps/worker`; build: `pnpm install --frozen-lockfile && pnpm turbo run build --filter=worker...`; start: `pnpm start --filter worker`.

Builds must go through `turbo run build --filter=<app>...` (not a bare `pnpm build --filter <app>`), because the `<app>...` suffix tells Turborepo to build the app's `packages/*` workspace dependencies first via the `dependsOn: ["^build"]` rule in `turbo.json`. Every internal package publishes through `dist/` (its `package.json` `main` field), so skipping that step leaves `dist/` missing and the service crashes on start with `Cannot find module '@tutor/...'`.

`pnpm install --frozen-lockfile` requires a committed `pnpm-lock.yaml` at the repo root that matches every `package.json` — regenerate and commit it (`pnpm install`) after any dependency or workspace-package-name change, or the install step fails immediately.

## Per-service dashboard settings (required)

Each Railway service **must** have its **Root Directory** (Settings → Source) set to the app's folder — `apps/web`, `apps/api`, or `apps/worker` respectively, matching the table above. Railway only reads a service's `railway.json` from within that service's Root Directory; if Root Directory is left at `/` (the default), Railpack scans the monorepo root `package.json` instead, finds no `start` script, and fails with "No start command detected."

Because Railpack's package-manager detection (the step that installs pnpm via Corepack) also only scans the Root Directory's `package.json`, every `apps/*/package.json` carries its own `"packageManager": "pnpm@9.12.0"` field — without it, Railpack scoped to a subfolder assumes plain npm/Node, never installs pnpm, and the build command fails with `pnpm: not found`. Keep this field in sync with the root `package.json`'s `packageManager` value if you ever bump the pnpm version.

For the same reason, `turbo` is listed as a `devDependency` in every `apps/*/package.json`, not just the repo root. pnpm only symlinks a package's bin into that package's own `node_modules/.bin`; with Root Directory scoped to `apps/web` (etc.), `pnpm turbo run build ...` runs from inside that folder, and if `turbo` is only declared at the workspace root it fails with `Command "turbo" not found`. Keep the `turbo` devDependency version in sync across the root and every app if you ever bump it.

If Railway executes from the repository root, keep the commands exactly as above. After deployment, run `pnpm db:seed` once from the API service shell to create demo users and Algebra Foundations curriculum. If Redis is absent locally, worker behavior falls back synchronously for MVP jobs.
