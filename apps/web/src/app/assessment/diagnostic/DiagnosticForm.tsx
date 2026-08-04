'use client';
import { useState, type FormEvent } from 'react';
import Link from 'next/link';
import { postJson } from '../../lib';

type DiagnosticItem = {
  id: string;
  type: 'MULTIPLE_CHOICE' | 'SHORT_ANSWER' | 'TRUE_FALSE';
  prompt: string;
  choices: string[] | null;
  learningObjective: { id: string; code: string; title: string } | null;
};

type AttemptResult = { id: string; score: number; status: string };

export default function DiagnosticForm({
  items,
  learnerId,
}: {
  items: DiagnosticItem[];
  learnerId: string;
}) {
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AttemptResult | null>(null);

  const setAnswer = (itemId: string, value: string) =>
    setAnswers((prev) => ({ ...prev, [itemId]: value }));

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const unanswered = items.filter((q) => !answers[q.id]?.trim());
    if (unanswered.length) {
      setError(`Please answer all questions (${unanswered.length} remaining).`);
      return;
    }
    setSubmitting(true);
    try {
      const attempt = await postJson('/assessment/attempts', {
        learnerId,
        responses: items.map((q) => ({ itemId: q.id, response: answers[q.id] })),
      });
      setResult(attempt);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not submit the diagnostic.');
    } finally {
      setSubmitting(false);
    }
  }

  if (result) {
    return (
      <div className="card">
        <h1 className="text-2xl font-bold">Diagnostic complete</h1>
        <p className="mt-2 text-lg">Score: {Math.round(result.score * 100)}%</p>
        <p className="text-slate-600">Your mastery and recommendations have been updated.</p>
        <div className="mt-4 flex gap-3">
          <Link className="btn" href="/dashboard">
            View dashboard
          </Link>
          <Link className="btn" href="/tutor">
            Ask tutor
          </Link>
        </div>
      </div>
    );
  }

  return (
    <form className="card" onSubmit={handleSubmit}>
      <h1 className="text-2xl font-bold">Diagnostic Assessment</h1>
      <p className="mb-4">Answer these sampled questions, then submit for grading.</p>
      {items.map((q) => (
        <fieldset key={q.id} className="mb-4 border-t pt-3">
          <legend className="font-semibold">
            {q.learningObjective?.code}: {q.prompt}
          </legend>
          {q.choices?.length ? (
            q.choices.map((c) => (
              <label key={c} className="block">
                <input
                  name={q.id}
                  type="radio"
                  checked={answers[q.id] === c}
                  onChange={() => setAnswer(q.id, c)}
                />{' '}
                {c}
              </label>
            ))
          ) : (
            <input
              className="mt-2 w-full rounded-xl border p-2"
              type="text"
              value={answers[q.id] ?? ''}
              onChange={(e) => setAnswer(q.id, e.target.value)}
              placeholder="Your answer"
            />
          )}
        </fieldset>
      ))}
      {error && <p className="mb-3 text-red-600">{error}</p>}
      <button className="btn" type="submit" disabled={submitting}>
        {submitting ? 'Submitting…' : 'Submit diagnostic'}
      </button>
    </form>
  );
}
