import type { LearnerMastery, LearningObjective, RecommendationResult } from '@tutor/shared';
export function recommendNextAction(input: {
  learnerId: string;
  objectives: LearningObjective[];
  masteries: LearnerMastery[];
  prerequisites: Record<string, string[]>;
  assessmentAttemptCount: number;
  resources?: Record<string, string>;
  now?: Date;
}): RecommendationResult {
  const { learnerId, objectives, masteries, prerequisites } = input;
  if (input.assessmentAttemptCount === 0)
    return {
      learnerId,
      actionType: 'TAKE_DIAGNOSTIC',
      reason:
        'Start with a diagnostic so the tutor can estimate mastery and find prerequisite gaps.',
      confidence: 0.95,
      alternatives: [
        {
          actionType: 'ASK_TUTOR',
          reason: 'Ask for help if you want guidance before the diagnostic.',
        },
      ],
    };
  const m = new Map(masteries.map((x) => [x.learningObjectiveId, x]));
  for (const lo of objectives) {
    const weak = (prerequisites[lo.id] || [])
      .map((id) => m.get(id))
      .filter((x) => x && x.masteryScore < 0.7)
      .sort((a, b) => a!.masteryScore - b!.masteryScore)[0];
    if (weak && (m.get(lo.id)?.status === 'PRACTICING' || (m.get(lo.id)?.masteryScore ?? 0) < 0.6))
      return {
        learnerId,
        actionType: 'REMEDIATE_PREREQUISITE',
        targetLearningObjectiveId: weak.learningObjectiveId,
        reason: `Recommended because "${lo.title}" depends on a prerequisite where current mastery is ${Math.round(weak.masteryScore * 100)}%.`,
        confidence: 0.88,
        alternatives: [
          {
            actionType: 'PRACTICE_LO',
            targetLearningObjectiveId: lo.id,
            reason: 'Continue practicing the current learning objective.',
          },
        ],
      };
  }
  const low = objectives
    .map((o) => ({ o, m: m.get(o.id) }))
    .find((x) => (x.m?.masteryScore ?? 0) < 0.6);
  if (low)
    return {
      learnerId,
      actionType: 'PRACTICE_LO',
      targetLearningObjectiveId: low.o.id,
      targetResourceId: input.resources?.[low.o.id],
      reason: `Practice "${low.o.title}" because mastery is below 60%.`,
      confidence: 0.82,
      alternatives: [
        {
          actionType: 'ASK_TUTOR',
          targetLearningObjectiveId: low.o.id,
          reason: 'Ask the tutor for one guided hint.',
        },
      ],
    };
  const stale = masteries.find(
    (x) =>
      x.status === 'MASTERED' &&
      x.lastPracticedAt &&
      Date.now() - new Date(x.lastPracticedAt).getTime() > 1000 * 60 * 60 * 24 * 14,
  );
  if (stale)
    return {
      learnerId,
      actionType: 'REVIEW_LO',
      targetLearningObjectiveId: stale.learningObjectiveId,
      reason: 'Review a previously mastered objective that has not been practiced recently.',
      confidence: 0.7,
      alternatives: [],
    };
  const next = objectives.find((o) => !m.get(o.id) || m.get(o.id)?.status !== 'MASTERED');
  return {
    learnerId,
    actionType: next ? 'START_NEW_LO' : 'COMPLETE_ASSESSMENT',
    targetLearningObjectiveId: next?.id,
    reason: next
      ? `You have unlocked "${next.title}" based on prerequisite mastery.`
      : 'All current objectives are mastered; complete a checkpoint assessment.',
    confidence: 0.76,
    alternatives: [],
  };
}
