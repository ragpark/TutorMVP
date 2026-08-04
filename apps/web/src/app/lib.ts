export const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:4000';
export async function getJson(path: string) {
  try {
    const r = await fetch(`${API}${path}`, { cache: 'no-store' });
    return r.ok ? await r.json() : null;
  } catch {
    return null;
  }
}
export async function postJson(path: string, body: unknown) {
  const r = await fetch(`${API}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    cache: 'no-store',
  });
  if (!r.ok) {
    const detail = await r.text().catch(() => '');
    throw new Error(`Request to ${path} failed (${r.status})${detail ? `: ${detail}` : ''}`);
  }
  return r.json();
}
export async function getLearnerId(): Promise<string | null> {
  const learner = await getJson('/learners/demo');
  return learner?.id ?? null;
}
