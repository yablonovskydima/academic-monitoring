from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from import_service.models.group import Group


class GroupRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_full_by_id(self, group_id: int) -> Group | None:
        return self.session.scalars(
            select(Group)
            .options(joinedload(Group.students))
            .where(Group.id == group_id)
        ).unique().first()

    def get_all(self) -> list[Group]:
        return list(self.session.scalars(select(Group)).all())

    def get_by_id(self, group_id: int) -> Group | None:
        return self.session.scalars(
            select(Group).where(Group.id == group_id)
        ).first()

    def create(self, group: Group) -> Group:
        self.session.add(group)
        self.session.commit()
        self.session.refresh(group)
        return group

    def bulk_create(self, groups: list[Group]) -> None:
        self.session.add_all(groups)
        self.session.commit()

    def update(self, group_id: int, **fields) -> Group | None:  # todo dto for update
        group = self.get_by_id(group_id)
        if group is None:
            return None
        for key, value in fields.items():
            setattr(group, key, value)
        self.session.commit()
        self.session.refresh(group)
        return group