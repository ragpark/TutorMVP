# Railway Deployment

Create a Railway project connected to the GitHub monorepo. Add services: `web`, `api`, `worker`, PostgreSQL, and Redis. Configure variables from `.env.example`; use Railway-provided `DATABASE_URL` and `REDIS_URL`.

Recommended settings:
- web root: `apps/web`; build: `pnpm install --frozen-lockfile && pnpm build --filter web`; start: `pnpm start --filter web`.
- api root: `apps/api`; build: `pnpm install --frozen-lockfile && pnpm db:generate && pnpm build --filter api`; start: `pnpm db:migrate && pnpm start --filter api`.
- worker root: `apps/worker`; build: `pnpm install --frozen-lockfile && pnpm build --filter worker`; start: `pnpm start --filter worker`.

If Railway executes from the repository root, keep the commands exactly as above. After deployment, run `pnpm db:seed` once from the API service shell to create demo users and Algebra Foundations curriculum. If Redis is absent locally, worker behavior falls back synchronously for MVP jobs.
