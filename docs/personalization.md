# Personal profiles and daily references (`test` branch)

Signed-in users can save their age, height, current weight, formula sex coefficient,
activity level, and muscle-gain or fat-loss goal. NutriChat calculates an approximate
daily energy reference and protein, fat and carbohydrate amounts. The calculation
runs in Python without Qwen, network requests or model-generated nutrition numbers.
The existing meal workflow remains available without a profile.

Use [the isolated account preview](accounts.md) at <http://localhost:8001/app>.
Fill in the personal profile card and select an activity level, then save. Edit and
save again to recalculate; reload or sign back in to restore the saved profile.
Unsaved edits hide the old reference so it is not presented as a new calculation.
If another tab saves first, the stale tab must explicitly reload before saving.

## Inputs and scope

| Field | Accepted input |
| --- | --- |
| `age_years` | Integer, 18–80 years |
| `height_cm` | Finite number, 120–220 cm |
| `weight_kg` | Finite number, 30–250 kg |
| `sex` | `male` or `female`, selecting the equation coefficient |
| `goal` | `gain_muscle` or `lose_fat` |
| `activity_level` | `sedentary`, `light`, `moderate` or `high` |

These are implementation bounds for a simplified adult tool, not definitions of
healthy measurements. Sex coefficients are limitations of the selected equation,
not a gender-identity classification. There are no inferred/default body values,
and activity is an explicit choice covering daily work, movement and exercise.
Age is saved as entered, not derived from a birth date or incremented automatically.
Users should update it and their current measurements when needed.

The feature is intended for general healthy adult reference, not pregnancy,
breastfeeding, children, clinical diet management or predictions of body composition.
The [NIDDK Body Weight Planner](https://www.niddk.nih.gov/bwp) also distinguishes adult
use and pregnancy/breastfeeding exclusions; NutriChat does not implement its model.

## Calculation version `mifflin-1990-nutrichat-v1`

Resting energy uses the simplified Mifflin–St Jeor equation:

```text
resting_kcal = 10 × weight_kg + 6.25 × height_cm − 5 × age_years + coefficient
coefficient = +5 (male) or −161 (female)
```

This predicts resting expenditure, not total daily needs. The original study used
498 adults aged 19–78; the UI's 18–80 bound is a product scope choice, not evidence
of validation at every accepted age or body size. See [Mifflin et al., 1990,
PMID 2305711](https://pubmed.ncbi.nlm.nih.gov/2305711/).

The following are **project assumptions**, not rules established by that paper:

| Activity | Multiplier |
| --- | --- |
| Sedentary | 1.2 |
| Light | 1.375 |
| Moderate | 1.55 |
| High | 1.725 |

Estimated maintenance energy is resting energy times the activity multiplier.
The muscle-gain reference adds 5%; the fat-loss reference subtracts 10%. These modest
fixed adjustments are a starting assumption, not individualized treatment or a
promise about muscle gain, weight-loss speed or outcomes. Exercise calories are not
added separately, because the selected activity multiplier already represents activity.

The initial macro split is 25% of energy from protein, 30% from fat and 45% from
carbohydrate, for both goals. Grams use 4/9/4 kcal per gram respectively. This split
lies inside the adult AMDR ranges, but is not a sports-specific optimum or an
assessment of the user's actual protein needs. The adult ranges are protein
10–35%, fat 20–35% and carbohydrate 45–65% of energy. See [Health Canada's reference
tables](https://www.canada.ca/en/health-canada/services/food-nutrition/healthy-eating/dietary-reference-intakes/tables/reference-values-macronutrients.html).

Calculations use decimal arithmetic. Displayed goal energy rounds half-up to the
nearest 10 kcal; all macro values are calculated from that displayed energy and
rounded half-up to 0.1 g. Resting/maintenance energy and BMI are returned to one
decimal. Rounding does not imply measurement precision or a statistical confidence
interval. BMI is used internally for the low-weight fat-loss guard, not displayed
as a diagnosis.

For a synthetic 30-year-old using the male coefficient, 180 cm, 80 kg and moderate
activity: resting energy is 1780 kcal and estimated maintenance is 2759 kcal.
Muscle-gain reference: about 2900 kcal, 181.3 g protein, 96.7 g fat and 326.3 g
carbohydrate. Fat-loss reference: about 2480 kcal, 155 g protein, 82.7 g fat and
279 g carbohydrate. These are test examples, not advice for a real individual.

## When no target is generated

The API saves valid inputs but returns `status: needs_review` with **all four target
values null** when any automatic-output guard applies:

- Fat-loss goal with unrounded BMI below 18.5 (`underweight_fat_loss`). This guard
  uses the adult low-BMI boundary described by [NHLBI](https://www.nhlbi.nih.gov/health/heart-healthy-living/healthy-weight).
- Unrounded proposed energy below 1500 kcal for the male coefficient or 1200 for
  the female coefficient (`low_energy_reference`). These are conservative product
  boundaries; they do not establish a universal minimum intake or prove that any
  value above them is suitable.
- Proposed energy below estimated resting expenditure (`below_resting_reference`),
  a defensive guard for future configuration changes. Current multipliers and goal
  adjustments do not produce this case for validated inputs.

The application does not silently replace an unavailable reference with zero, a
clamped target or a maintenance prescription. It retains the inputs, explains the
limitation and keeps ordinary meal estimation available.

## API, persistence and privacy

`GET /profile` returns `{profile: null, reference: null}` until the current user
creates a profile. `PUT /profile` requires all six input fields and `revision`:

```json
{
  "age_years": 30,
  "height_cm": 180,
  "weight_kg": 80,
  "sex": "male",
  "goal": "gain_muscle",
  "activity_level": "moderate",
  "revision": 0
}
```

Use revision 0 only for the initial save and the latest saved revision for updates.
Success returns 200 with `{profile, reference}`; the first saved revision is 1.
Conflicts return 409. Strict input validation rejects unknown fields, numeric
strings, booleans, fractional ages, non-finite numbers and out-of-range values.
Invalid requests return 422 without reflecting the personal input values. A client
cannot supply an owner, calculated totals or formula version.

The authenticated session determines the profile owner. There is no other-user
profile route; anonymous requests return 401. PUT requires the existing custom
security header and origin checks. Responses use `Cache-Control: no-store`.
The browser does not save body measurements in localStorage and clears the profile
display on logout. Profile inputs are not sent to the AI service, worker or Qwen.

Migration `20261027_0007` creates `user_profiles`, with one row per user and database
constraints matching input ranges/enums. It preserves existing users, sessions,
analyses, cases and jobs. Atomic revision checks prevent silent lost updates. A
downgrade drops profiles only and therefore loses their data; take a backup before
any real rollback.

Only the latest input snapshot is stored; reference values are computed on read
with the versioned calculator. Changing current weight does **not** create a daily
weight log. Use [daily tracking](tracking.md) to record measurements independently
and view 30-day calorie/weight trends. Changing a daily weight does not update the
profile or recalculate its reference. Target history, medical history, Google login
and password recovery remain separate future work.
