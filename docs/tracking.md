# Daily calorie and weight tracking (`test` branch)

Signed-in users can keep one daily record per date and review a rolling 30-day
window. This is an intake/measurement diary, not a prediction of weight change or
an assessment of whether an individual diet is adequate. Meal calories remain
estimates; a day with only some meals recorded is still an incomplete intake log.

## Workflow

1. Select the meal's date before confirming a completed estimate. Confirmed meals
   contribute to that date's automatic calorie total; other statuses do not.
2. In the daily record form, choose a date and enter a weight measurement, a total
   calorie intake, or both. Weight is in kilograms and energy is in kcal.
3. Leave the calorie field empty to use confirmed meals. A manual total replaces
   the meal sum; it is never added to it. Clear the manual field and save to return
   to automatic mode. Clear weight and save to remove that day's measurement.
4. Choose the last day of the chart window to review 30 consecutive dates. The
   expandable detail table exposes the same numbers and calorie sources.

There is one value per user/date, so a later weight entry for the same date updates
that measurement. Daily weights do not automatically change the profile's current
weight, nutrition reference, or goal. Update the profile separately when desired.
The charts do not apply today's nutrition reference retrospectively to older days.

## Meaning of the chart

- Missing calories or weight are null and shown as gaps, never inferred zeros.
  An explicitly entered calorie total of zero is preserved as a recorded value.
- A meal-derived total is the sum of confirmed estimates, not evidence of a full
  day's food intake. The form/table shows the source and confirmed meal count.
- Average calories use only dates with an available calorie total. Missing days
  do not enter the denominator; weight-only days do not count as calorie days.
- Weight change compares the last and first measurements inside the window. It is
  unavailable with fewer than two recorded dates, and is not a forecast or a rate.
- No smoothing, gap filling, extrapolation, target-achievement score or automatic
  diet adjustment is applied. The window is 30 days, not a calendar month.

## Dates and API

All date boundaries use **Asia/Hong_Kong**. A date is an exact `YYYY-MM-DD` string,
from `2000-01-01` through the server's current Hong Kong date. Future recording is
not supported. A chart end date must be at least `2000-01-30` so its full window
falls within the recording range.

`POST /analyses/{id}/confirm` accepts the current revision and optional
`consumed_on`. Omit it to use the current Hong Kong date. The saved meal date is
returned by analysis reads. Confirmation still locks the meal and its date; review
both before confirming. Existing revision/state rules prevent confirming the same
record twice. Separately created duplicate meals remain separate records because
analysis creation has no idempotency key.

`GET /daily-records/{date}` returns an empty daily view with revision 0 when no
manual record exists. Confirmed meals can already contribute to that view.
`PUT /daily-records/{date}` requires both nullable fields and the current revision:

```json
{"revision": 0, "weight_kg": 75.2, "manual_calories": 2100}
```

Accepted bounds are finite weight 30–250 kg and manual calories 0–20000 kcal.
These are input bounds, not recommended measurements/intakes. Numeric strings,
booleans, unknown fields and non-finite numbers are rejected. The first save uses
revision 0 and returns revision 1; later saves use the returned revision. A stale
or competing save returns 409 and requires an explicit reload. A row with both
values null is retained with its revision so clearing does not erase concurrency
history.

Daily responses contain `date`, `revision`, `weight_kg`, `manual_calories`,
`meal_calories`, `meal_count`, `calories` and `calorie_source`. Source is `manual`,
`meals` or null. With no confirmed meals, `meal_calories` is null and count is 0.

`GET /tracking?end=YYYY-MM-DD` returns `timezone`, `today`, `start_date`, `end_date`,
30 chronologically ordered daily views and `summary`. Omitting `end` selects today.
Summary fields are `recorded_days`, `average_calories`, `weight_entries`,
`first_weight_kg`, `last_weight_kg` and `weight_change_kg`. Nullable results remain
null when their prerequisite observations are absent.

## Persistence and privacy

The session determines ownership for every read, aggregate and write. Clients cannot
supply another user ID. Unowned legacy meals and other users' meals are excluded.
Mutations require the existing security header and origin checks; responses use
`Cache-Control: no-store`. Validation errors omit submitted health values. The
browser clears diary/chart data on logout and does not persist it in localStorage.
Tracking makes no AI service, Qwen or external charting request.

Migration `20261027_0008` adds `daily_records` and `analyses.consumed_on`. Older
confirmed meals receive the Hong Kong date of `confirmed_at`, falling back to
`created_at` when necessary. This preserves a usable daily grouping but cannot
recover an unknown actual meal date. Other saved meal fields remain unchanged.
Unconfirmed meals retain a null date. Downgrading removes daily records and meal
dates, so take a backup before rolling back a real database.

The application stores current daily values, not a full edit audit or historical
target snapshots. The current increment stays on `test`; the public ECS app and
the original branches remain unchanged.
