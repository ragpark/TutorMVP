export type Role = 'ADMIN' | 'TEACHER' | 'LEARNER';
export type CognitiveLevel =
  'REMEMBER' | 'UNDERSTAND' | 'APPLY' | 'ANALYZE' | 'EVALUATE' | 'CREATE';
export type MasteryStatus =
  'NOT_STARTED' | 'INTRODUCED' | 'PRACTICING' | 'PARTIAL' | 'MASTERED' | 'NEEDS_REVIEW';
export type AssessmentItemType = 'MULTIPLE_CHOICE' | 'SHORT_ANSWER' | 'TRUE_FALSE';
export type GraphNodeType =
  | 'COURSE'
  | 'MODULE'
  | 'TOPIC'
  | 'LEARNING_OBJECTIVE'
  | 'CONCEPT'
  | 'RESOURCE'
  | 'ASSESSMENT_ITEM'
  | 'MISCONCEPTION';
export type GraphEdgeType =
  | 'CONTAINS'
  | 'REQUIRES_CONCEPT'
  | 'DEPENDS_ON'
  | 'UNLOCKS'
  | 'ASSESSES'
  | 'TEACHES'
  | 'REMEDIATES'
  | 'RELATED_TO';
export type RecommendationActionType =
  | 'START_NEW_LO'
  | 'REVIEW_LO'
  | 'PRACTICE_LO'
  | 'REMEDIATE_PREREQUISITE'
  | 'TAKE_DIAGNOSTIC'
  | 'ASK_TUTOR'
  | 'COMPLETE_ASSESSMENT';
export type LearningObjective = {
  id: string;
  code: string;
  title: string;
  description: string;
  cognitiveLevel: CognitiveLevel;
  estimatedMinutes: number;
  difficulty: number;
  topicId?: string;
};
export type LearnerMastery = {
  learnerId: string;
  learningObjectiveId: string;
  masteryScore: number;
  confidenceScore: number;
  attemptCount: number;
  lastPracticedAt?: Date | string | null;
  lastAssessedAt?: Date | string | null;
  status: MasteryStatus;
};
export type RecommendationResult = {
  learnerId: string;
  actionType: RecommendationActionType;
  targetLearningObjectiveId?: string;
  targetResourceId?: string;
  reason: string;
  confidence: number;
  alternatives: Array<{
    actionType: RecommendationActionType;
    targetLearningObjectiveId?: string;
    reason: string;
  }>;
};
