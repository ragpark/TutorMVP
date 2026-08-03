import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

const AssessmentItemType = {
  MULTIPLE_CHOICE: 'MULTIPLE_CHOICE',
  SHORT_ANSWER: 'SHORT_ANSWER',
  TRUE_FALSE: 'TRUE_FALSE',
} as const;

const CognitiveLevel = {
  UNDERSTAND: 'UNDERSTAND',
  APPLY: 'APPLY',
} as const;

const GraphEdgeType = {
  CONTAINS: 'CONTAINS',
  DEPENDS_ON: 'DEPENDS_ON',
  UNLOCKS: 'UNLOCKS',
  ASSESSES: 'ASSESSES',
  TEACHES: 'TEACHES',
  REQUIRES_CONCEPT: 'REQUIRES_CONCEPT',
} as const;

const GraphNodeType = {
  COURSE: 'COURSE',
  MODULE: 'MODULE',
  TOPIC: 'TOPIC',
  LEARNING_OBJECTIVE: 'LEARNING_OBJECTIVE',
  CONCEPT: 'CONCEPT',
  RESOURCE: 'RESOURCE',
  ASSESSMENT_ITEM: 'ASSESSMENT_ITEM',
} as const;

const RecommendationActionType = { TAKE_DIAGNOSTIC: 'TAKE_DIAGNOSTIC' } as const;
const Role = { ADMIN: 'ADMIN', TEACHER: 'TEACHER', LEARNER: 'LEARNER' } as const;

const courseSeed = {
  title: 'Algebra Foundations',
  description: 'Adaptive path through variables, equations, and graphing basics.',
  modules: [
    {
      title: 'Variables and Expressions',
      topics: [
        {
          title: 'Variables',
          learningObjectives: [
            {
              code: 'ALG-VAR-001',
              title: 'Understand variables',
              description: 'Explain how letters can represent unknown or changing values.',
              cognitiveLevel: CognitiveLevel.UNDERSTAND,
              estimatedMinutes: 15,
              difficulty: 1,
              concepts: ['variable', 'unknown value'],
              resources: [
                {
                  title: 'Intro to Variables',
                  type: 'ARTICLE',
                  content:
                    'A variable is a symbol that can stand for an unknown or changing number. Learners identify variables in context before using them in expressions.',
                },
              ],
              assessmentItems: [
                {
                  type: AssessmentItemType.MULTIPLE_CHOICE,
                  prompt: 'In the expression x + 4, what does x represent?',
                  choices: [
                    'A value that can vary or be unknown',
                    'Always the number 4',
                    'An operation',
                    'An equal sign',
                  ],
                  correctAnswer: 'A value that can vary or be unknown',
                  explanation: 'A variable is a symbol for an unknown or changing value.',
                },
                {
                  type: AssessmentItemType.TRUE_FALSE,
                  prompt: 'A variable can represent an unknown number.',
                  choices: ['true', 'false'],
                  correctAnswer: 'true',
                  explanation: 'Variables are commonly used to represent unknown quantities.',
                },
              ],
            },
          ],
        },
        {
          title: 'Expressions',
          learningObjectives: [
            {
              code: 'ALG-EXP-001',
              title: 'Evaluate simple expressions',
              description: 'Substitute values into simple algebraic expressions and simplify.',
              cognitiveLevel: CognitiveLevel.APPLY,
              estimatedMinutes: 20,
              difficulty: 2,
              prerequisites: ['ALG-VAR-001'],
              concepts: ['expression', 'substitution', 'order of operations'],
              resources: [
                {
                  title: 'Evaluating Expressions Practice',
                  type: 'PRACTICE',
                  content:
                    'Substitute the given number for the variable, then simplify using arithmetic and the order of operations.',
                },
              ],
              assessmentItems: [
                {
                  type: AssessmentItemType.MULTIPLE_CHOICE,
                  prompt: 'Evaluate 3x + 2 when x = 4.',
                  choices: ['9', '12', '14', '20'],
                  correctAnswer: '14',
                  explanation: 'Substitute 4 for x: 3(4) + 2 = 12 + 2 = 14.',
                },
                {
                  type: AssessmentItemType.SHORT_ANSWER,
                  prompt: 'Evaluate a - 5 when a = 12.',
                  correctAnswer: '7',
                  explanation: 'Replace a with 12 and subtract 5.',
                },
              ],
            },
          ],
        },
      ],
    },
    {
      title: 'Equations',
      topics: [
        {
          title: 'Inverse Operations',
          learningObjectives: [
            {
              code: 'ALG-EQ-001',
              title: 'Understand inverse operations',
              description: 'Explain how inverse operations undo each other to isolate a variable.',
              cognitiveLevel: CognitiveLevel.UNDERSTAND,
              estimatedMinutes: 15,
              difficulty: 2,
              prerequisites: ['ALG-VAR-001'],
              concepts: ['inverse operation', 'equality', 'operation pair'],
              resources: [
                {
                  title: 'Inverse Operations Explainer',
                  type: 'ARTICLE',
                  content:
                    'Addition and subtraction are inverse operations, as are multiplication and division. Use an inverse operation on both sides to keep equality true.',
                },
              ],
              assessmentItems: [
                {
                  type: AssessmentItemType.MULTIPLE_CHOICE,
                  prompt: 'Which operation undoes multiplication by 5?',
                  choices: ['Add 5', 'Subtract 5', 'Divide by 5', 'Multiply by 5'],
                  correctAnswer: 'Divide by 5',
                  explanation: 'Division is the inverse operation of multiplication.',
                },
              ],
            },
          ],
        },
        {
          title: 'One-Step Equations',
          learningObjectives: [
            {
              code: 'ALG-EQ-002',
              title: 'Solve one-step equations',
              description:
                'Solve one-step linear equations in one variable while preserving equality.',
              cognitiveLevel: CognitiveLevel.APPLY,
              estimatedMinutes: 25,
              difficulty: 3,
              prerequisites: ['ALG-VAR-001', 'ALG-EQ-001'],
              concepts: ['equation', 'equality', 'inverse operation'],
              resources: [
                {
                  title: 'Solving One-Step Equations Guide',
                  type: 'ARTICLE',
                  content:
                    'Identify the operation affecting the variable, apply the inverse operation to both sides, and check the solution.',
                },
              ],
              assessmentItems: [
                {
                  type: AssessmentItemType.MULTIPLE_CHOICE,
                  prompt: 'Solve x + 7 = 12.',
                  choices: ['x = 5', 'x = 7', 'x = 12', 'x = 19'],
                  correctAnswer: 'x = 5',
                  explanation: 'Subtract 7 from both sides: x = 5.',
                },
              ],
            },
          ],
        },
        {
          title: 'Two-Step Equations',
          learningObjectives: [
            {
              code: 'ALG-EQ-003',
              title: 'Solve two-step equations',
              description:
                'Solve two-step linear equations by reversing operations in the correct order.',
              cognitiveLevel: CognitiveLevel.APPLY,
              estimatedMinutes: 30,
              difficulty: 4,
              prerequisites: ['ALG-EQ-002'],
              concepts: ['equation', 'inverse operation', 'multi-step reasoning'],
              resources: [
                {
                  title: 'Solving Two-Step Equations Guide',
                  type: 'ARTICLE',
                  content:
                    'Undo addition or subtraction first, then undo multiplication or division. Check by substituting the answer into the original equation.',
                },
              ],
              assessmentItems: [
                {
                  type: AssessmentItemType.MULTIPLE_CHOICE,
                  prompt: 'Solve 2x + 3 = 11.',
                  choices: ['x = 3', 'x = 4', 'x = 7', 'x = 14'],
                  correctAnswer: 'x = 4',
                  explanation: 'Subtract 3 to get 2x = 8, then divide by 2.',
                },
              ],
            },
          ],
        },
      ],
    },
    {
      title: 'Graphing Basics',
      topics: [
        {
          title: 'Coordinate Plane',
          learningObjectives: [
            {
              code: 'ALG-GRAPH-001',
              title: 'Understand coordinate pairs',
              description:
                'Interpret ordered pairs on the coordinate plane using x- and y-coordinates.',
              cognitiveLevel: CognitiveLevel.UNDERSTAND,
              estimatedMinutes: 20,
              difficulty: 2,
              concepts: ['coordinate pair', 'x-axis', 'y-axis', 'origin'],
              resources: [
                {
                  title: 'Coordinate Plane Basics',
                  type: 'ARTICLE',
                  content:
                    'An ordered pair is written (x, y). Move along the x-axis first, then move parallel to the y-axis.',
                },
              ],
              assessmentItems: [
                {
                  type: AssessmentItemType.MULTIPLE_CHOICE,
                  prompt: 'In the ordered pair (3, 5), which number is the y-coordinate?',
                  choices: ['3', '5', '8', 'The origin'],
                  correctAnswer: '5',
                  explanation: 'The second number in an ordered pair is the y-coordinate.',
                },
              ],
            },
          ],
        },
      ],
    },
  ],
} as const;

const expectedLearningObjectiveCount = courseSeed.modules.reduce(
  (moduleTotal, moduleSeed) =>
    moduleTotal +
    moduleSeed.topics.reduce(
      (topicTotal, topicSeed) => topicTotal + topicSeed.learningObjectives.length,
      0,
    ),
  0,
);

type GraphNodeTypeValue = (typeof GraphNodeType)[keyof typeof GraphNodeType];
type GraphEdgeTypeValue = (typeof GraphEdgeType)[keyof typeof GraphEdgeType];
type CreatedNode = { id: string; type: GraphNodeTypeValue; entityId: string };

async function createGraphNode(
  type: GraphNodeTypeValue,
  entityId: string,
  label: string,
  metadata?: object,
) {
  return prisma.graphNode.upsert({
    where: { type_entityId: { type, entityId } },
    update: { label, metadata },
    create: { type, entityId, label, metadata },
  });
}

async function createGraphEdge(
  source: CreatedNode,
  target: CreatedNode,
  type: GraphEdgeTypeValue,
  weight = 1,
  metadata?: object,
) {
  return prisma.graphEdge.create({
    data: {
      sourceNodeId: source.id,
      targetNodeId: target.id,
      type,
      weight,
      metadata,
    },
  });
}

async function main() {
  const existingCourse = await prisma.course.findFirst({ where: { title: courseSeed.title } });

  if (existingCourse && process.env.FORCE_SEED !== 'true') {
    const [learningObjectiveCount, graphNodeCount, graphEdgeCount] = await Promise.all([
      prisma.learningObjective.count({
        where: { topic: { module: { courseId: existingCourse.id } } },
      }),
      prisma.graphNode.count(),
      prisma.graphEdge.count(),
    ]);

    if (
      learningObjectiveCount >= expectedLearningObjectiveCount &&
      graphNodeCount > 0 &&
      graphEdgeCount > 0
    ) {
      console.log(
        `${courseSeed.title} seed data already exists. Set FORCE_SEED=true to reset and reseed the MVP dataset.`,
      );
      return;
    }

    console.log(
      `${courseSeed.title} seed data is incomplete; resetting and reseeding the MVP dataset.`,
    );
  }

  const [, , learner] = await Promise.all([
    prisma.user.upsert({
      where: { email: 'admin@example.com' },
      update: { name: 'Demo Admin', role: Role.ADMIN },
      create: { email: 'admin@example.com', name: 'Demo Admin', role: Role.ADMIN },
    }),
    prisma.user.upsert({
      where: { email: 'teacher@example.com' },
      update: { name: 'Demo Teacher', role: Role.TEACHER },
      create: { email: 'teacher@example.com', name: 'Demo Teacher', role: Role.TEACHER },
    }),
    prisma.user.upsert({
      where: { email: 'learner@example.com' },
      update: { name: 'Demo Learner', role: Role.LEARNER },
      create: {
        email: 'learner@example.com',
        name: 'Demo Learner',
        role: Role.LEARNER,
        profile: { create: { gradeLevel: '8', goals: 'Build algebra confidence' } },
      },
    }),
  ]);

  await prisma.learnerProfile.upsert({
    where: { learnerId: learner.id },
    update: { gradeLevel: '8', goals: 'Build algebra confidence' },
    create: { learnerId: learner.id, gradeLevel: '8', goals: 'Build algebra confidence' },
  });

  await prisma.$transaction([
    prisma.recommendation.deleteMany({ where: { learnerId: learner.id } }),
    prisma.learnerActivity.deleteMany({ where: { learnerId: learner.id } }),
    prisma.learnerMastery.deleteMany({ where: { learnerId: learner.id } }),
    prisma.assessmentResponse.deleteMany(),
    prisma.assessmentAttempt.deleteMany({ where: { learnerId: learner.id } }),
    prisma.tutorMessage.deleteMany(),
    prisma.tutorSession.deleteMany({ where: { learnerId: learner.id } }),
    prisma.graphEdge.deleteMany(),
    prisma.graphNode.deleteMany(),
    prisma.assessmentItem.deleteMany(),
    prisma.resource.deleteMany(),
    prisma.learningObjective.deleteMany(),
    prisma.concept.deleteMany(),
    prisma.topic.deleteMany(),
    prisma.module.deleteMany(),
    prisma.course.deleteMany({ where: { title: courseSeed.title } }),
  ]);

  const nodesByKey = new Map<string, CreatedNode>();
  const learningObjectiveIdsByCode = new Map<string, string>();

  const course = await prisma.course.create({
    data: { title: courseSeed.title, description: courseSeed.description },
  });
  const courseNode = await createGraphNode(GraphNodeType.COURSE, course.id, course.title, {
    description: course.description,
  });
  nodesByKey.set(`course:${course.title}`, courseNode);

  for (const [moduleIndex, moduleSeed] of courseSeed.modules.entries()) {
    const module = await prisma.module.create({
      data: { title: moduleSeed.title, order: moduleIndex + 1, courseId: course.id },
    });
    const moduleNode = await createGraphNode(GraphNodeType.MODULE, module.id, module.title, {
      order: module.order,
    });
    await createGraphEdge(courseNode, moduleNode, GraphEdgeType.CONTAINS, 1, {
      order: module.order,
    });

    for (const [topicIndex, topicSeed] of moduleSeed.topics.entries()) {
      const topic = await prisma.topic.create({
        data: { title: topicSeed.title, order: topicIndex + 1, moduleId: module.id },
      });
      const topicNode = await createGraphNode(GraphNodeType.TOPIC, topic.id, topic.title, {
        order: topic.order,
      });
      await createGraphEdge(moduleNode, topicNode, GraphEdgeType.CONTAINS, 1, {
        order: topic.order,
      });

      for (const learningObjectiveSeed of topicSeed.learningObjectives) {
        const learningObjective = await prisma.learningObjective.create({
          data: {
            code: learningObjectiveSeed.code,
            title: learningObjectiveSeed.title,
            description: learningObjectiveSeed.description,
            cognitiveLevel: learningObjectiveSeed.cognitiveLevel,
            estimatedMinutes: learningObjectiveSeed.estimatedMinutes,
            difficulty: learningObjectiveSeed.difficulty,
            topicId: topic.id,
          },
        });
        learningObjectiveIdsByCode.set(learningObjective.code, learningObjective.id);

        const learningObjectiveNode = await createGraphNode(
          GraphNodeType.LEARNING_OBJECTIVE,
          learningObjective.id,
          learningObjective.title,
          {
            code: learningObjective.code,
            cognitiveLevel: learningObjective.cognitiveLevel,
            estimatedMinutes: learningObjective.estimatedMinutes,
            difficulty: learningObjective.difficulty,
          },
        );
        nodesByKey.set(`lo:${learningObjective.code}`, learningObjectiveNode);
        await createGraphEdge(topicNode, learningObjectiveNode, GraphEdgeType.CONTAINS, 1, {
          order: topic.order,
        });

        await prisma.learnerMastery.create({
          data: { learnerId: learner.id, learningObjectiveId: learningObjective.id },
        });

        for (const conceptTitle of learningObjectiveSeed.concepts) {
          const slug = conceptTitle.replaceAll(' ', '-');
          const concept = await prisma.concept.upsert({
            where: { slug },
            update: {
              title: conceptTitle,
              description: `Core Algebra Foundations concept: ${conceptTitle}`,
            },
            create: {
              slug,
              title: conceptTitle,
              description: `Core Algebra Foundations concept: ${conceptTitle}`,
            },
          });
          const conceptNode = await createGraphNode(
            GraphNodeType.CONCEPT,
            concept.id,
            concept.title,
            { slug: concept.slug },
          );
          await createGraphEdge(learningObjectiveNode, conceptNode, GraphEdgeType.REQUIRES_CONCEPT);
        }

        for (const resourceSeed of learningObjectiveSeed.resources) {
          const resource = await prisma.resource.create({
            data: { ...resourceSeed, learningObjectiveId: learningObjective.id },
          });
          const resourceNode = await createGraphNode(
            GraphNodeType.RESOURCE,
            resource.id,
            resource.title,
            { type: resource.type },
          );
          await createGraphEdge(resourceNode, learningObjectiveNode, GraphEdgeType.TEACHES);
        }

        for (const assessmentItemSeed of learningObjectiveSeed.assessmentItems) {
          const assessmentItem = await prisma.assessmentItem.create({
            data: { ...assessmentItemSeed, learningObjectiveId: learningObjective.id },
          });
          const assessmentNode = await createGraphNode(
            GraphNodeType.ASSESSMENT_ITEM,
            assessmentItem.id,
            assessmentItem.prompt,
            {
              type: assessmentItem.type,
            },
          );
          await createGraphEdge(assessmentNode, learningObjectiveNode, GraphEdgeType.ASSESSES);
        }
      }
    }
  }

  for (const moduleSeed of courseSeed.modules) {
    for (const topicSeed of moduleSeed.topics) {
      for (const learningObjectiveSeed of topicSeed.learningObjectives) {
        const sourceNode = nodesByKey.get(`lo:${learningObjectiveSeed.code}`);
        if (!sourceNode || !('prerequisites' in learningObjectiveSeed)) continue;

        for (const prerequisiteCode of learningObjectiveSeed.prerequisites ?? []) {
          const prerequisiteNode = nodesByKey.get(`lo:${prerequisiteCode}`);
          if (!prerequisiteNode)
            throw new Error(`Missing prerequisite LO node: ${prerequisiteCode}`);

          await createGraphEdge(sourceNode, prerequisiteNode, GraphEdgeType.DEPENDS_ON);
          await createGraphEdge(prerequisiteNode, sourceNode, GraphEdgeType.UNLOCKS);
        }
      }
    }
  }

  await prisma.recommendation.create({
    data: {
      learnerId: learner.id,
      actionType: RecommendationActionType.TAKE_DIAGNOSTIC,
      reason: 'Start with the Algebra Foundations diagnostic to initialize mastery scores.',
      confidence: 0.95,
      alternatives: [...learningObjectiveIdsByCode.entries()].map(([code, id]) => ({
        code,
        learningObjectiveId: id,
      })),
    },
  });

  console.log(
    `Seeded ${courseSeed.title}: ${courseSeed.modules.length} modules, ${learningObjectiveIdsByCode.size} learning objectives, and a connected knowledge graph.`,
  );
}

main()
  .catch((error) => {
    console.error(error);
    process.exitCode = 1;
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
