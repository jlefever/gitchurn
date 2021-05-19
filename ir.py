import enum
from typing import NamedTuple, List


class Chunk(NamedTuple):
    new_lineno: int
    new_offset: int
    del_lineno: int
    del_offset: int


class ChangeKind(enum.Enum):
    ADDED = "A"
    MODIFIED = "M"
    DELETED = "D"


class Change(NamedTuple):
    filename: str
    kind: ChangeKind
    chunks: List[Chunk]


class Commit(NamedTuple):
    hash: str
    parents: List[str]
    changes: List[Change]
