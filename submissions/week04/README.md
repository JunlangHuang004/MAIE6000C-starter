# Week 4 - NutriChat Proposal

## 1. Concise Proposal Summary

- Team: [GROUP 1]
- Members: [CAO, Jiacheng;
            HUANG, Junlang;
            HUANG, Yixing;
            ZHOU, Ran]
- Repository: [https://github.com/Zr21340398/MAIE6000C-starter.git]
- Checkpoint: `w04-proposal`

NutriChat helps adults estimate calories, protein, fat, and carbohydrates from a meal description with explicit gram quantities. Built on the course starter, the API stores a meal and job; a polling worker calls the AI service, calculates nutrition from reference data, and saves the result. The user retrieves, corrects, and confirms it. The first version supports a small food catalog and runs as a local demo.

## 2. Milestone Plan

| Week | Target |
|---|---|
| Week 5 | API contract, meal/job persistence, verified reference data, and model access |
| Week 7 | End-to-end processing, result retrieval, correction, confirmation, and visible failure |
| Week 9 | Reproducible Docker deployment and documented setup |
| Week 11 | Reliability tests, logging, and basic performance checks |
| Week 12 | Tested final workflow and demonstration |

## 3. Artifact Index

- [README.md](../../README.md): project introduction, members, and workflow.
- [docs/architecture.md](../../docs/architecture.md): architecture diagram, schema, states, worker/AI plan, and scope.
- [submissions/week04/README.md](README.md): proposal summary, milestones, artifact index, and AI disclosure.

## 4. AI Use Statement

AI assisted with suggestions for the project architecture and development workflow. See [submissions/week04/AI_USE_STATEMENT.md](AI_USE_STATEMENT.md).
