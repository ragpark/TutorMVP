'use client';
import { useState, type FormEvent } from 'react';
import { postJson } from '../lib';

type ChatMessage = { role: 'learner' | 'tutor'; content: string };

export default function TutorChat({
  sessionId,
  learningObjectiveTitle,
}: {
  sessionId: string;
  learningObjectiveTitle: string;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'tutor',
      content: `Tell me what you tried first on ${learningObjectiveTitle}. I will ask one guiding question at a time rather than just giving the final answer.`,
    },
  ]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSend(e: FormEvent) {
    e.preventDefault();
    const message = input.trim();
    if (!message || sending) return;
    setError(null);
    setMessages((prev) => [...prev, { role: 'learner', content: message }]);
    setInput('');
    setSending(true);
    try {
      const reply = await postJson(`/tutor/sessions/${sessionId}/messages`, { message });
      setMessages((prev) => [...prev, { role: 'tutor', content: reply.content }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The tutor could not respond.');
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="card">
      <div className="flex flex-col gap-3">
        {messages.map((m, i) => (
          <div
            key={i}
            className={
              m.role === 'tutor' ? 'rounded-xl bg-indigo-50 p-4' : 'rounded-xl bg-slate-100 p-4'
            }
          >
            {m.content}
          </div>
        ))}
      </div>
      {error && <p className="mt-3 text-red-600">{error}</p>}
      <form onSubmit={handleSend}>
        <textarea
          className="mt-4 w-full rounded-xl border p-3"
          placeholder="Ask for help with the current learning objective"
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <button className="btn mt-3" type="submit" disabled={sending}>
          {sending ? 'Sending…' : 'Send'}
        </button>
      </form>
    </section>
  );
}
