import Link from 'next/link';
import { getJson, learnerId } from '../lib';
export default async function Learn() {
  const rec = await getJson(`/learners/${learnerId}/recommendations/current`);
  const los = (await getJson('/learning-objectives')) ?? [];
  const lo = los.find((x: any) => x.id === rec?.targetLearningObjectiveId) || los[0];
  const prereqs = lo ? await getJson(`/learning-objectives/${lo.id}/prerequisites`) : [];
  const concepts = lo ? await getJson(`/learning-objectives/${lo.id}/concepts`) : [];
  return (
    <div className="card">
      <h1 className="text-2xl font-bold">Recommended Activity</h1>
      <p>{rec?.reason ?? 'Take the diagnostic to personalize this page.'}</p>
      {lo && (
        <>
          <h2 className="mt-4 text-xl font-bold">
            {lo.code}: {lo.title}
          </h2>
          <p>{lo.description}</p>
          <h3 className="mt-3 font-bold">Concepts</h3>
          <p>{concepts.map((c: any) => c.title).join(', ') || 'Seed required'}</p>
          <h3 className="mt-3 font-bold">Prerequisites</h3>
          <p>{prereqs.map((p: any) => p.title).join(', ') || 'None'}</p>
          <div className="mt-4 flex gap-3">
            <Link className="btn" href="/assessment/diagnostic">
              Assessment
            </Link>
            <Link className="btn" href="/tutor">
              Tutor help
            </Link>
          </div>
        </>
      )}
    </div>
  );
}
