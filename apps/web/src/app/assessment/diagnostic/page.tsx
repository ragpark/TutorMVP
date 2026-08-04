import { getJson, getLearnerId } from '../../lib';
import DiagnosticForm from './DiagnosticForm';

export default async function Diagnostic() {
  const learnerId = await getLearnerId();
  if (!learnerId) {
    return (
      <div className="card">
        <h1 className="text-2xl font-bold">Diagnostic Assessment</h1>
        <p className="mt-2">No demo learner is seeded yet. Run `pnpm db:seed` and reload.</p>
      </div>
    );
  }

  const items = (await getJson('/assessment/diagnostic')) ?? [];
  if (!items.length) {
    return (
      <div className="card">
        <h1 className="text-2xl font-bold">Diagnostic Assessment</h1>
        <p className="mt-2">No diagnostic questions are available yet. Seed the curriculum first.</p>
      </div>
    );
  }

  return <DiagnosticForm items={items} learnerId={learnerId} />;
}
