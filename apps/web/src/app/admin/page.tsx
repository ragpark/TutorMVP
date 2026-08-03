import Link from 'next/link';
export default function Admin() {
  return (
    <div className="card">
      <h1 className="text-2xl font-bold">Admin Overview</h1>
      <p>Manage demo curriculum and inspect graph validation.</p>
      <Link className="btn mt-4 inline-block" href="/admin/graph">
        Validate graph
      </Link>
    </div>
  );
}
