from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import Cohort, CohortMembership, Institution


class InstitutionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_institution(self, name: str) -> Institution:
        institution = Institution(name=name)
        self.session.add(institution)
        self.session.commit()
        self.session.refresh(institution)
        return institution

    def create_cohort(self, institution_id: int, name: str) -> Cohort:
        cohort = Cohort(institution_id=institution_id, name=name)
        self.session.add(cohort)
        self.session.commit()
        self.session.refresh(cohort)
        return cohort

    def add_member(self, cohort_id: int, student_id: int) -> CohortMembership:
        membership = CohortMembership(cohort_id=cohort_id, student_profile_id=student_id)
        self.session.add(membership)
        self.session.commit()
        self.session.refresh(membership)
        return membership

    def get_cohort(self, cohort_id: int) -> Cohort | None:
        return self.session.get(Cohort, cohort_id)
