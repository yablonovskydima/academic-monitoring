from abc import ABC, abstractmethod


class DataSource(ABC):
    @abstractmethod
    def load_groups(self) -> list[dict]: ...

    @abstractmethod
    def load_students(self) -> list[dict]: ...