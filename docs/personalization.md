# Personal profiles and daily references

Signed-in users can save their age, height, current weight, formula sex coefficient,
activity level, muscle-gain or fat-loss goal, strength-training answer and reference
scope. NutriChat calculates an approximate daily energy reference and protein, fat
and carbohydrate amounts when those inputs fit its automatic-output policy. The
calculation runs in Python without Qwen, network requests or model-generated
nutrition numbers. The existing meal workflow remains available without a profile.

Use [the merged preview](integration.md) at <http://localhost:8005/app>. Complete the
personal profile card, explicitly confirm the two scope/training answers, then
save. Edit and save again to recalculate; reload or sign back in to restore the
saved profile. Unsaved edits hide the old reference so it is not presented as a new
calculation. If another tab saves first, the stale tab must explicitly reload
before saving. Profiles saved before v2 need the new confirmations before targets
can be shown again.

## Inputs and scope

| Field | Accepted input |
| --- | --- |
| `age_years` | Integer, 18–80 years |
| `height_cm` | Finite number, 120–220 cm |
| `weight_kg` | Finite number, 30–250 kg |
| `sex` | `male` or `female`, selecting the equation coefficient |
| `goal` | `gain_muscle` or `lose_fat` |
| `activity_level` | `sedentary`, `light`, `moderate` or `high` |
| `strength_training` | Explicit `true` or `false`; `null` means unanswered |
| `reference_scope` | `general_adult`, `professional_guidance` or unanswered `null` |

These are implementation bounds for a simplified adult tool, not definitions of
healthy measurements. Sex coefficients are limitations of the selected equation,
not a gender-identity classification. There are no inferred/default body values,
and activity is an explicit choice covering daily work, movement and exercise.
Strength training is a separate answer: a high activity level does not imply it.
Age is saved as entered, not derived from a birth date or incremented automatically.
Users should update it and their current measurements when needed.

`general_adult` confirms use of a general adult reference. Pregnancy, breastfeeding
and circumstances requiring individual clinical nutrition guidance fall outside
this scope; `professional_guidance` saves that choice and withholds automatic
targets. This confirmation is not a medical assessment. Neither the profile nor a
successful calculation establishes nutritional suitability or predicts body
composition. The calculator does not model training dose, body fat, medical
history or changes in energy expenditure over time.

## Calculation version `mifflin-evidence-2026-v2`

Resting energy uses the simplified Mifflin–St Jeor equation:

```text
resting_kcal = 10 × weight_kg + 6.25 × height_cm − 5 × age_years + coefficient
coefficient = +5 (male) or −161 (female)
```

This predicts resting expenditure, not total daily needs. The original study used
498 adults aged 19–78, including normal-weight and obese participants. The app's
18–80 age bounds and BMI eligibility rules are product choices, not the study's
validation limits. See [Mifflin et al., 1990, PMID 2305711](https://pubmed.ncbi.nlm.nih.gov/2305711/).

The following activity factors are approximate **project assumptions**, not rules
established by that paper:

| Activity | Multiplier |
| --- | --- |
| Sedentary | 1.2 |
| Light | 1.375 |
| Moderate | 1.55 |
| High | 1.725 |

Estimated maintenance energy is resting energy times the activity factor. Exercise
calories are not added separately to this reference, because the selected factor
already represents activity. Goal energy is then calculated as follows:

```text
gain_muscle: proposed_kcal = maintenance_kcal × 1.05
lose_fat:    deficit_kcal = min(maintenance_kcal × 0.15, 500)
            proposed_kcal = maintenance_kcal − deficit_kcal
```

The 5% surplus and the smaller of a 15% deficit or 500 kcal/day are **app starting
policies informed by evidence**. No cited guideline mandates this exact combined
rule, and 500 kcal is not a universal safety threshold. The evidence and its
population limits are separated from implementation choices in the
[source and limitation map](personalization-sources.md). Clinical recommendations
of 500–750 kcal/day deficits for some overweight/obese adults are not a universal
rule for normal-BMI users. There is no automatic prediction or guarantee of a
weekly weight-loss rate, muscle gain or other outcome.

### Protein, fat and carbohydrate

Protein is based on the saved **actual body weight**, not a fixed percentage of
energy, ideal weight or estimated lean mass:

| Goal and training answer | Starting protein amount | Evidence context, not a personalized range |
| --- | --- | --- |
| Muscle gain, strength training `true` | 1.6 g/kg/day | 1.6–2.2 g/kg/day with resistance training |
| Fat loss, strength training `true` | 1.8 g/kg/day | 1.6–2.2 g/kg/day with resistance training |
| Fat loss, strength training `false` | 1.4 g/kg/day | 1.2–1.6 g/kg/day for the general population |

The exact starting values are app choices. The cited ranges are context from the
[2026 ISSN position stand](https://pmc.ncbi.nlm.nih.gov/articles/PMC13665703/), not an
individual assessment or a claim that the app optimizes lean athletes' cutting
diets. Muscle-gain output requires a positive training answer; missing answers
are not treated as `false`.

Fat starts at 30% of displayed goal energy. It is reduced only as needed to leave
at least 45% of energy for carbohydrate, while staying at or above 20% for ages
19–80 or 25% at age 18. Protein energy is 4 kcal/g, fat is 9 kcal/g, and carbohydrate
receives the remaining energy at 4 kcal/g:

```text
protein_g = weight_kg × selected_protein_g_per_kg
protein_kcal = protein_g × 4
fat_kcal = min(goal_kcal × 0.30, goal_kcal × 0.55 − protein_kcal)
fat_g = fat_kcal / 9
carbs_g = (goal_kcal − protein_kcal − fat_kcal) / 4
```

The macro checks require protein to supply 10–35% of energy (10–30% at age 18),
fat 20–30% (25–30% at age 18), and carbohydrate 45–65% and at least 130 g/day.
If the combination cannot fit, all targets are withheld; protein is not silently
reduced to fit. These output bounds are informed by
[Health Canada's DRI tables](https://www.canada.ca/en/health-canada/services/food-nutrition/healthy-eating/dietary-reference-intakes/tables/reference-values-macronutrients.html).
They define this product's scope, not universal safe/unsafe intake boundaries.

### Rounding and examples

Calculations use decimal arithmetic. Displayed goal energy rounds half-up to the
nearest 10 kcal. Macro allocation and its compatibility checks use that displayed
energy and unrounded gram amounts; displayed grams round half-up to 0.1 g. Resting
and maintenance energy and BMI are returned to one decimal. Independent rounding
can make the displayed macro-energy sum differ slightly from displayed calories.

For a synthetic 25-year-old using the male coefficient, 175 cm, 70 kg, moderate
activity, strength training `true` and `general_adult` scope, resting energy is
1673.75 kcal and maintenance is 2594.3125 kcal before rounding:

| Goal | Unrounded proposed energy | Displayed energy | Protein | Fat | Carbohydrate |
| --- | --- | --- | --- | --- | --- |
| Muscle gain | 2724.028125 kcal | 2720 kcal | 112.0 g | 90.7 g | 364.0 g |
| Fat loss | 2205.165625 kcal | 2210 kcal | 126.0 g | 73.7 g | 260.8 g |

These examples verify the arithmetic, not the accuracy of an individual's energy
needs. Decimal precision and repeatable test results do not create measurement
precision, a confidence interval or evidence that a real person should eat these
amounts.

## When no target is generated

The API saves valid inputs but returns `status: needs_review` with **all four target
values null** when any automatic-output guard applies:

- Scope is unanswered (`scope_confirmation_required`) or is
  `professional_guidance` (`professional_guidance_required`).
- Training is unanswered (`training_confirmation_required`), or muscle gain is
  selected with training `false` (`strength_training_required`).
- Unrounded BMI is below 18.5 or at least 40, for either goal. These are self-service
  eligibility boundaries, not diagnoses, age-specific BMI classifications or
  claimed Mifflin equation validation limits. A BMI between them does not establish
  that weight loss is indicated or that automatic targets are appropriate. Codes:
  `underweight_reference` and `high_bmi_reference`, respectively.
- Unrounded proposed energy is below 1500 kcal for the male coefficient or 1200
  for the female coefficient (`low_energy_reference`). These retained product
  floors do not establish universal minimum intakes or prove that values above
  them are suitable.
- Unrounded proposed energy is below estimated resting expenditure
  (`below_resting_reference`). This is a defensive product check, not a
  physiological rule that establishes safe intake.
- The macro allocation fails the age-appropriate protein/fat bounds or the
  carbohydrate checks described above (`macro_distribution_out_of_scope`).

The application retains the inputs, explains whether confirmation or review is
needed, and keeps ordinary meal estimation available. It does not substitute zero,
a clamped target or a maintenance prescription. Daily balance output also remains
withheld while the profile reference is ineligible; recording meals and daily data
does not override the scope checks.

## API, persistence and privacy

`GET /profile` returns `{profile: null, reference: null}` until the current user
creates a profile. `PUT /profile` requires the original six input fields and
`revision`; current clients also send explicit answers for the two new fields:

```json
{
  "age_years": 25,
  "height_cm": 175,
  "weight_kg": 70,
  "sex": "male",
  "goal": "gain_muscle",
  "activity_level": "moderate",
  "strength_training": true,
  "reference_scope": "general_adult",
  "revision": 0
}
```

Use revision 0 only for the initial save and the latest saved revision for updates.
Success returns 200 with `{profile, reference}`; the first saved revision is 1.
Conflicts return 409. Strict validation rejects unknown fields, numeric strings,
booleans in numeric fields, fractional ages, non-finite numbers, out-of-range
values, and invalid confirmation types/enums. Invalid requests return 422 without
reflecting personal input values. A client cannot supply an owner, calculated
totals or formula version.

An older client may omit the two new fields. On a new profile they remain `null`;
on an existing profile omitted fields preserve saved answers through
`exclude_unset=True`. An explicit `null` clears that answer and withholds targets
until reconfirmed. A saved `false` training answer is an actual answer, distinct
from omission or `null`.

The reference includes the calculation version, source links and effective energy
adjustment. `goal_adjustment` reports the actual fractional change after the
500 kcal cap, while `energy_adjustment_kcal` reports the signed calorie change.
For eligible profiles, the selected protein rate and contextual range are returned
as both g/kg and grams, alongside macro energy percentages. These contextual range
endpoints are not alternative prescribed targets and are not used to bypass the
macro checks. They remain null when targets are withheld.

The authenticated session determines the profile owner. There is no other-user
profile route; anonymous requests return 401. PUT requires the existing custom
security header and origin checks. Responses use `Cache-Control: no-store`.
The browser does not save body measurements in localStorage and clears the profile
display on logout. Profile inputs are not sent to the AI service, worker or Qwen.

Migration `20261027_0007` created `user_profiles`, with one row per user and database
constraints matching input ranges/enums. Migration `20261121_0011` adds nullable
`strength_training` and `reference_scope` columns without defaults or backfilling
consent. Existing profiles therefore require explicit reconfirmation. Atomic
revision checks prevent silent lost updates. Downgrading `0011` discards only the
new answers; rolling back `0007` drops profiles and their data. Back up data before
a real rollback.

Only the latest input snapshot is stored; reference values are computed on read
with the versioned calculator. The v2 change does not rewrite the `w13-final`
snapshot or its historical evidence. Changing current profile weight does **not**
create a daily weight log. Use [daily tracking](tracking.md) to record measurements
independently and view 30-day calorie/weight trends. Changing a daily weight does
not update the profile or recalculate its reference. Target history, medical
history, Google login and password recovery remain separate future work.
