import { getJson } from '../lib';
export default async function Tutor() {
  const los = (await getJson('/learning-objectives')) ?? [];
  const lo = los[0];
  return (
    <div className="grid gap-6">
      <section className="card">
        <h1 className="text-2xl font-bold">Curriculum-grounded Tutor</h1>
        <p>
          Current LO: {lo ? `${lo.code} ${lo.title}` : 'Seed the curriculum to load LO context.'}
        </p>
        <p className="text-slate-600">
          The API sends LO, concepts, prerequisites, mastery, and recommendation context to the
          tutor provider.
        </p>
      </section>
      <section className="card">
        <div className="rounded-xl bg-indigo-50 p-4">
          Tutor: Tell me what you tried first. I will ask one guiding question at a time rather than
          just giving the final answer.
        </div>
        <textarea
          className="mt-4 w-full rounded-xl border p-3"
          placeholder="Ask for help with the current learning objective"
        />
        <button className="btn mt-3">Send</button>
      </section>
    </div>
  );
}
