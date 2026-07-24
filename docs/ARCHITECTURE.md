# Architecture

The system is a GitHub monorepo with three deployable Railway services. The web app calls the API through `NEXT_PUBLIC_API_URL`. The API owns Prisma persistence and coordinates graph traversal, assessment grading, mastery updates, recommendations, and tutor sessions. The worker consumes Redis-backed BullMQ jobs when Redis is configured.

Data flow: seeded curriculum creates courses/modules/topics/LOs, concepts, resources, assessment items, graph nodes, and graph edges. Diagnostic submissions create attempts/responses, update `LearnerMastery`, and save a `Recommendation`. Tutor requests assemble LO, concept, prerequisite, mastery, and recommendation context before calling a provider.
