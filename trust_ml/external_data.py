from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Iterable
from urllib.request import urlretrieve
from zipfile import ZipFile

import pandas as pd

from .features import _clamp
from .schemas import FeatureVectorExample


UCI_STUDENT_PERFORMANCE_URL = "https://archive.ics.uci.edu/static/public/320/student+performance.zip"


def download_uci_student_performance(data_dir: str | Path = "data/uci") -> Path:
    target_dir = Path(data_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    zip_path = target_dir / "student_performance.zip"

    if zip_path.exists():
        return zip_path

    urlretrieve(UCI_STUDENT_PERFORMANCE_URL, zip_path)
    return zip_path


def _row_to_feature_vector(row: pd.Series) -> dict[str, float]:
    g1 = float(row["G1"]) / 20.0
    g2 = float(row["G2"]) / 20.0
    g3 = float(row["G3"]) / 20.0
    studytime = float(row["studytime"]) / 4.0
    failures = _clamp(float(row["failures"]) / 4.0)
    absences = _clamp(float(row["absences"]) / 30.0)
    traveltime = _clamp(float(row["traveltime"]) / 4.0)
    family_support = 1.0 if row["famsup"] == "yes" else 0.0
    school_support = 1.0 if row["schoolsup"] == "yes" else 0.0
    activities = 1.0 if row["activities"] == "yes" else 0.0
    higher = 1.0 if row["higher"] == "yes" else 0.0
    internet = 1.0 if row["internet"] == "yes" else 0.0
    paid = 1.0 if row["paid"] == "yes" else 0.0
    family_education = _clamp((float(row["Medu"]) + float(row["Fedu"])) / 8.0)

    accuracy_easy = _clamp(g1)
    accuracy_medium = _clamp(g2)
    accuracy_hard = _clamp(g3)
    accuracy_overall = _clamp((g1 + g2 + g3) / 3.0)
    weighted_accuracy = _clamp((g1 * 1.0 + g2 * 1.5 + g3 * 2.0) / 4.5)
    confidence_mean = _clamp(
        0.35 * g2
        + 0.25 * g3
        + 0.15 * studytime
        + 0.10 * higher
        + 0.10 * internet
        + 0.05 * family_education
    )
    calibration_gap = _clamp((abs(g1 - g2) + abs(g2 - g3)) / 2.0)
    overconfidence_rate = _clamp(
        0.45 * higher * max(0.0, 0.55 - g3)
        + 0.20 * (1.0 - g3) * paid
        + 0.20 * max(0.0, absences - 0.35)
        + 0.15 * failures
    )
    underconfidence_rate = _clamp(
        0.50 * max(0.0, g3 - confidence_mean)
        + 0.25 * max(0.0, 0.6 - higher) * g3
        + 0.25 * school_support * g3
    )
    answer_change_rate = _clamp(0.5 * failures + 0.3 * absences + 0.2 * traveltime)
    resume_claim_alignment = _clamp(
        0.50 * g3 + 0.20 * studytime + 0.15 * activities + 0.15 * higher
    )
    resume_claim_inflation = _clamp(
        0.45 * max(0.0, higher - g3)
        + 0.25 * paid * max(0.0, 0.6 - g2)
        + 0.30 * failures
    )
    project_evidence_strength = _clamp(
        0.35 * activities + 0.25 * internet + 0.20 * paid + 0.20 * family_support
    )
    external_evidence_score = _clamp(
        0.55 * project_evidence_strength + 0.25 * internet + 0.20 * family_education
    )
    stage_progression_drop = _clamp(max(0.0, g1 - g3))
    confidence_correct_delta = _clamp(1.0 - calibration_gap * 0.8)
    confidence_volatility = _clamp(abs(g1 - g3) + abs(g2 - g3))
    avg_time_ratio = _clamp(
        0.35 * (1.0 - studytime) + 0.25 * traveltime + 0.25 * absences + 0.15 * failures
    )
    fundamentals = _clamp(
        0.45 * g3 + 0.20 * studytime + 0.15 * family_education + 0.20 * higher
    )
    projects = _clamp(
        0.40 * project_evidence_strength + 0.25 * activities + 0.20 * internet + 0.15 * g2
    )
    dsa = _clamp(0.50 * g2 + 0.35 * g3 + 0.15 * studytime)

    return {
        "accuracy_overall": round(accuracy_overall, 6),
        "weighted_accuracy": round(weighted_accuracy, 6),
        "avg_time_ratio": round(avg_time_ratio, 6),
        "confidence_mean": round(confidence_mean, 6),
        "confidence_calibration_gap": round(calibration_gap, 6),
        "overconfidence_rate": round(overconfidence_rate, 6),
        "underconfidence_rate": round(underconfidence_rate, 6),
        "answer_change_rate": round(answer_change_rate, 6),
        "resume_claim_alignment": round(resume_claim_alignment, 6),
        "resume_claim_inflation": round(resume_claim_inflation, 6),
        "project_evidence_strength": round(project_evidence_strength, 6),
        "codeforces_rating_normalized": 0.0,
        "leetcode_solved_normalized": 0.0,
        "external_evidence_score": round(external_evidence_score, 6),
        "stage_progression_drop": round(stage_progression_drop, 6),
        "confidence_correct_delta": round(confidence_correct_delta, 6),
        "confidence_volatility": round(confidence_volatility, 6),
        "accuracy_easy": round(accuracy_easy, 6),
        "accuracy_medium": round(accuracy_medium, 6),
        "accuracy_hard": round(accuracy_hard, 6),
        "skill_score_dsa": round(dsa, 6),
        "skill_score_fundamentals": round(fundamentals, 6),
        "skill_score_projects": round(projects, 6),
    }


def _row_to_label(row: pd.Series) -> int:
    g3 = float(row["G3"])
    failures = float(row["failures"])
    absences = float(row["absences"])
    higher = row["higher"] == "yes"
    return int(g3 >= 12 and failures < 2 and absences <= 15 and higher)


def load_uci_feature_examples(zip_path: str | Path) -> list[FeatureVectorExample]:
    source = Path(zip_path)
    examples: list[FeatureVectorExample] = []

    with ZipFile(source) as archive:
        nested_name = None
        for name in archive.namelist():
            if name.endswith("student.zip"):
                nested_name = name
                break

        inner_archive = archive
        nested_handle = None
        if nested_name is not None:
            nested_handle = archive.open(nested_name)
            inner_archive = ZipFile(BytesIO(nested_handle.read()))

        try:
            for filename in ("student-mat.csv", "student-por.csv"):
                with inner_archive.open(filename) as handle:
                    frame = pd.read_csv(handle, sep=";")
                for _, row in frame.iterrows():
                    examples.append(
                        FeatureVectorExample(
                            features=_row_to_feature_vector(row),
                            readiness_label=_row_to_label(row),
                        )
                    )
        finally:
            if nested_handle is not None:
                nested_handle.close()
            if inner_archive is not archive:
                inner_archive.close()

    return examples


def load_or_download_uci_feature_examples(data_dir: str | Path = "data/uci") -> list[FeatureVectorExample]:
    zip_path = download_uci_student_performance(data_dir=data_dir)
    return load_uci_feature_examples(zip_path)
