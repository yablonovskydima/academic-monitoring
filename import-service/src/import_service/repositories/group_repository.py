from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from import_service.models.group import Group


class GroupRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_all(self) -> list[Group]:
         return list(self.session.scalars(select(Group)).all())

    def get_by_id(self, group_id: int) -> Group | None:
        return self.session.scalars(
            select(Group).where(Group.id == group_id)
        ).first()

    def get_full_by_id(self, group_id: int) -> Group | None:
        return self.session.scalars(
            select(Group)
            .options(joinedload(Group.students))
            .where(Group.id == group_id)
        ).unique().first()

    def save(self, group: Group) -> Group:
        self.session.add(group)
        self.session.commit()
        self.session.refresh(group)
        return group

    def bulk_save(self, groups: list[Group]) -> None:
        self.session.add_all(groups)
        self.session.commit()

    def delete(self, group_id: int) -> bool:
        group = self.get_by_id(group_id)
        if group is None:
            return False
        self.session.delete(group)
        self.session.commit()
        return True