# Trust Model Card

## Summary
- Selected model: `gradient_boosting`
- Training rows: `2196`
- External transfer rows: `1044`

## Metrics
- ROC AUC: `0.999424`
- Accuracy: `0.989526`
- Brier score: `0.02034`
- Log loss: `0.107556`

## Top Feature Drivers
- `weighted_accuracy`: `0.269796`
- `resume_claim_inflation`: `0.216721`
- `codeforces_rating_normalized`: `0.172493`
- `accuracy_hard`: `0.10707`
- `answer_change_rate`: `0.093537`
- `confidence_mean`: `0.047161`
- `avg_time_ratio`: `0.044403`
- `skill_score_fundamentals`: `0.034103`

## Limits
- This artifact is trained on synthetic cohorts derived from demo archetypes.
- The bluff index is a risk signal and not a fraud label.
- Real-world deployment needs first-party labeled outcomes, fairness checks, and consent controls.