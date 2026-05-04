# ML Model Research For The Trust Platform

## What The Current Product Actually Needs

The platform has three different modeling problems:

1. `Assessment ability estimation`
2. `Trust and readiness scoring from fused evidence`
3. `Roadmap and explanation generation`

These should not be forced into one model family.

## Best Model Families By Subproblem

### 1. Assessment Ability Estimation

Best base model family:

- `IRT` and `Bayesian IRT`

Why:

- it directly models learner ability and question difficulty
- it is interpretable enough for educational settings
- it matches staged assessments better than a generic classifier

Strong candidate to post-train:

- `py-irt`

### 2. Trust And Readiness Scoring

Best current practical family:

- calibrated tabular classifiers on engineered evidence features

Strong current choices:

- `XGBoost`
- `CatBoost`
- `TabPFN` for small to medium labeled datasets

Recommendation:

- use calibrated `XGBoost` or `CatBoost` when you have enough labeled first-party rows
- use `TabPFN` when the labeled dataset is still relatively small and you want a stronger foundation-model baseline

### 3. Sequential Interaction Modeling

Best research-grade family:

- knowledge tracing models

Most relevant bases:

- `AKT`
- `SAINT` and `SAINT+`
- `EduKTM` as a practical model zoo for experimentation

## Practical Recommendation For This Project

### Right now

- calibrated tree-based tabular model for trust and readiness
- heuristic plus evidence-based bluff index
- LLM or rules for roadmap explanations

### Next serious upgrade

- add `IRT` for question difficulty and latent ability
- keep a tabular fusion model on top of IRT outputs, external evidence, and resume alignment

### Best long-term stack

- `py-irt` or another Bayesian IRT layer for question and learner parameters
- `TabPFN` or `CatBoost/XGBoost` for fused trust and readiness scoring
- `AKT` or `SAINT+` for sequential learner modeling once enough interaction history exists

## Important Corrections To The Original Idea

- A generic LLM is not the best core scoring model here.
- A single end-to-end deep model is not the best first production system.
- There is no good public supervised dataset for direct `bluff detection`.
- The strongest production path is a layered system:
  - psychometrics for ability
  - tabular model for trust and readiness
  - language model for explanation and roadmap generation

## Sources

- TabPFN Nature paper: https://www.nature.com/articles/s41586-024-08328-6
- TabPFN official repository: https://github.com/PriorLabs/TabPFN
- py-irt paper: https://doi.org/10.1287/ijoc.2022.1250
- py-irt package: https://pypi.org/project/py-irt/
- AKT paper listing: https://www.kdd.org/kdd2020/accepted-papers/view/context-aware-attentive-knowledge-tracing.html
- CatBoost official docs: https://catboost.ai/docs/en/features/categorical-features.html
- XGBoost Python API docs: https://xgboost.readthedocs.io/en/release_3.0.0/python/python_api.html
- EduKTM model zoo: https://github.com/bigdata-ustc/EduKTM
