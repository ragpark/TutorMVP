import { getJson, getLearnerId, postJson } from '../lib';
import TutorChat from './TutorChat';

export default async function Tutor() {
  const learnerId = await getLearnerId();
  const los = (await getJson('/learning-objectives')) ?? [];
  const lo = los[0];

  if (!learnerId || !lo) {
    return (
      <div className="card">
        <h1 className="text-2xl font-bold">Curriculum-grounded Tutor</h1>
        <p>
          {!learnerId
            ? 'No demo learner is seeded yet. Run `pnpm db:seed` and reload.'
            : 'Seed the curriculum to load LO context.'}
        </p>
      </div>
    );
  }

  let session: { id: string } | null = null;
  let sessionError: string | null = null;
  try {
    session = await postJson('/tutor/sessions', {
      learnerId,
      currentLearningObjectiveId: lo.id,
    });
  } catch (err) {
    sessionError = err instanceof Error ? err.message : 'Could not start a tutor session.';
  }

  return (
    <div className="grid gap-6">
      <section className="card">
        <h1 className="text-2xl font-bold">Curriculum-grounded Tutor</h1>
        <p>
          Current LO: {lo.code} {lo.title}
        </p>
        <p className="text-slate-600">
          The API sends LO, concepts, prerequisites, mastery, and recommendation context to the
          tutor provider.
        </p>
      </section>
      {session ? (
        <TutorChat sessionId={session.id} learningObjectiveTitle={lo.title} />
      ) : (
        <section className="card">
          <p className="text-red-600">{sessionError}</p>
        </section>
      )}
    </div>
  );
}
