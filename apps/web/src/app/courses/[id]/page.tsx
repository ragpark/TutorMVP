import { getJson } from '../../lib';
export default async function Course({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const c = await getJson(`/courses/${id}`);
  return (
    <div className="card">
      <h1 className="text-2xl font-bold">{c?.title ?? 'Course detail'}</h1>
      {c?.modules?.map((m: any) => (
        <div key={m.id} className="mt-4">
          <h2 className="font-bold">{m.title}</h2>
          {m.topics.map((t: any) => (
            <div key={t.id} className="ml-4">
              <h3>{t.title}</h3>
              <ul className="list-disc ml-6">
                {t.learningObjectives.map((lo: any) => (
                  <li key={lo.id}>
                    {lo.code}: {lo.title}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
