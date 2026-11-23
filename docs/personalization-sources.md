# Personal reference v2: sources and limits

This map supports `mifflin-evidence-2026-v2`; the implemented policy is documented
in [Personal profiles and daily references](personalization.md). Sources were
checked on 2026-11-21. A study finding, a professional position statement and an
engineering decision have different roles. The studies below inform the choices;
none validates NutriChat's complete algorithm or guarantees an individual outcome.

## Evidence and the decision it informs

| Source and study context | What it supports | What remains an app decision or limitation |
| --- | --- | --- |
| [Mifflin et al. (1990), PMID 2305711](https://pubmed.ncbi.nlm.nih.gov/2305711/) — equation derived from measured resting expenditure in 498 adults aged 19–78, including normal-weight and obese participants. | The selected resting-energy equation and its sex coefficients. | The activity factors, goal adjustments, accepted ages 18–80 and BMI eligibility limits do not come from this paper. Prediction is not an individual measurement; BMI 40 is not asserted to be the equation's validation boundary. |
| [Helms et al. (2023)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10620361/) — trained lifters assigned maintenance, 5% or 15% surplus during eight weeks of resistance training; 17 completed. | Larger gains in body mass were more clearly associated with increased skinfolds than with increased muscle thickness, supporting restraint when choosing a surplus. | The small, short trial does not prove that 5% is optimal for every trainee. NutriChat selects 5% as a starting policy and requires confirmed strength training for muscle-gain output. |
| [Garthe et al. (2011), PMID 21558571](https://pubmed.ncbi.nlm.nih.gov/21558571/) — 24 athletes with resistance training, comparing slower and faster weight-loss regimens; achieved energy reductions were about 19% and 30%. | The slower regimen had more favorable lean-mass results in this setting, informing preference for a moderate deficit. | Neither arm tested NutriChat's exact 15% rule. Athlete results and achieved weekly changes are not promises for general users. |
| [Murphy and Koehler (2022; online 2021), PMID 34623696](https://pubmed.ncbi.nlm.nih.gov/34623696/) — meta-analysis and meta-regression of resistance training during energy deficit. | Deficits impaired lean-mass gains; the regression estimated no lean-mass gain at roughly 500 kcal/day deficit. The authors advise avoiding larger deficits when seeking to preserve lean mass with training. | A regression estimate about training adaptation is not a universal safe-intake cutoff. The 500 kcal cap, combined with a 15% cap for every eligible fat-loss profile, is NutriChat policy. |
| [Morton et al. (2018; online 2017), PMID 28698222](https://pubmed.ncbi.nlm.nih.gov/28698222/) ([journal results](https://bjsm.bmj.com/content/52/6/376)) — protein supplementation alongside resistance training in healthy adults. | Estimated protein-intake breakpoint for additional fat-free-mass benefit was 1.62 g/kg/day, with a wide 95% interval of 1.03–2.20; this informs the 1.6 g/kg gain starting value. | This is a population estimate, not a precise individual requirement or a universal upper limit. It does not establish NutriChat's exact 1.8 g/kg fat-loss target. |
| [ISSN position stand (2026)](https://pmc.ncbi.nlm.nih.gov/articles/PMC13665703/) — professional evidence synthesis on body-weight reduction. | Provides 1.2–1.6 g/kg/day for the general population and 1.6–2.2 g/kg/day with resistance training. It also discusses higher intake in lean, resistance-trained people under energy restriction. | NutriChat uses actual body weight and fixed starting values of 1.4, 1.6 or 1.8 g/kg. It does not implement the more specialized lean-athlete recommendations or assess body fat, training quality or clinical protein requirements. |
| [Health Canada DRI tables](https://www.canada.ca/en/health-canada/services/food-nutrition/healthy-eating/dietary-reference-intakes/tables/reference-values-macronutrients.html) — macronutrient reference values, including age-specific AMDRs. | At ages 19+, AMDRs are protein 10–35%, fat 20–35% and carbohydrate 45–65%; at age 18, the applicable protein/fat ranges are 10–30%/25–35%. The carbohydrate RDA is 130 g/day for these nonpregnant, nonlactating age groups. | The app's 30% nominal fat allocation, adjustment order and withholding behavior are engineering choices. AMDR endpoints and an RDA are not universal toxicity or safety thresholds. These checks do not assess complete dietary adequacy. |

The deficit rule is specifically `min(15% of estimated maintenance, 500 kcal/day)`.
The 15% figure is a modest starting choice informed by the direction of the
restriction evidence, not a number directly established by the Garthe comparison.
The 500 kcal cap draws on the training/lean-mass concern above, not a claim that any
smaller deficit is appropriate for every person.

The calculator also links [NICE NG246's dietary recommendations](https://www.nice.org.uk/guidance/ng246/chapter/Physical-activity-and-diet),
which place 800–1200 kcal/day diets within supported specialist care for defined
overweight/obesity populations. This supports keeping clinical diet management
outside the app's automatic scope; it does not establish the app's exact
1500/1200 kcal floors or guarantee suitability just above them. NICE's
[rationale](https://www.nice.org.uk/guidance/ng246/chapter/Rationale-and-impact)
explicitly describes choosing not to specify one universal deficit.

## Why a 500–750 kcal clinical recommendation is not the general rule

The [2013 AHA/ACC/TOS guideline for overweight and obesity](https://pmc.ncbi.nlm.nih.gov/articles/PMC5819889/)
includes 500 or 750 kcal/day deficits among options within a comprehensive
intervention for overweight/obese adults who would benefit from weight loss. Its
population and treatment context matter. It does not make those deficits mandatory
for normal-BMI users or validate an unsupervised calculation for everyone. NutriChat
does not treat that guideline as the source of its exact v2 deficit formula.

## Deliberate product boundaries

- The nullable training and scope answers prevent assumptions about old or
  incomplete profiles. Selecting general-adult scope is a user confirmation, not
  clinical screening.
- BMI below 18.5 or at least 40 withholds both goal types. These are product
  eligibility cutoffs across the accepted age range; they are not diagnoses or
  substitutes for age-appropriate clinical BMI interpretation.
- The retained 1500/1200 kcal floors and below-resting-energy check limit automatic
  output. They do not certify intake above those boundaries or prove that every
  lower intake is unsafe in every clinical setting.
- Protein/fat bounds follow the applicable DRI age group; fat is kept within the
  app's narrower 20–30% range at ages 19+ or 25–30% at age 18. When protein cannot
  fit alongside those fat bounds and at least 45% carbohydrate energy, the app
  withholds targets. The 130 g carbohydrate check is an additional scope check.
- Actual body weight is available directly from the profile. Using it does not
  estimate lean mass or establish that weight-based protein scales equally well
  across all body compositions. BMI and macro compatibility checks limit this
  simple implementation without silently substituting an invented ideal weight.

## What verification can and cannot establish

Unit and integration checks can establish reproducible decimal arithmetic,
rounding, input validation, eligibility behavior, migration compatibility and
privacy boundaries. The worked example in the main document was also calculated
independently from the formulas.

Those checks cannot establish a person's true resting expenditure, maintenance
energy, future adherence or changes in weight and muscle. The app does not convert
a nominal calorie deficit into a guaranteed weekly loss, and it does not claim
that references are accurate to the displayed decimal place. Historical
`w13-final` evidence describes the earlier version and remains unchanged.
