# Layman Router v2 Evaluation Rubric

Score each auto and always-deep response from 1 to 5 on correctness, completeness, instruction following, and required format. Use the same evaluator and prompt order for both routes.

Release gates:

- Auto price-table estimate from measured usage is at least 20% lower than always-deep.
- Automatic validator pass rate is no more than 2 percentage points below always-deep.
- Mean human score is no more than 0.2 points below always-deep on the 5-point scale.
- No high-risk task routes below deep.
- Fallback rate is at most 10%.

Do not use the production summary endpoint's counterfactual estimate as measured savings. Live eval results contain separate real calls for both routes.
