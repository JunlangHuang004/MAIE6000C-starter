# NutriChat - Text-Based Meal Nutrition Estimator

NutriChat estimates calories, protein, fat, and carbohydrates from a meal description. Users provide supported foods and their weights in grams, then review, correct, and confirm the saved estimate.

## Team Members

- [CAO, Jiacheng;
   HUANG, Junlang;
   HUANG, Yixing;
   ZHOU, Ran]

## Workflow

The user submits a meal -> the API stores a job -> a worker uses AI and nutrition reference data -> the result is saved -> the user reviews and confirms it.
