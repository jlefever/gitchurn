# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import enum
import itertools as it
from typing import Iterator, List, NamedTuple


class Chunk(NamedTuple):
    new_lineno: int
    new_offset: int
    del_lineno: int
    del_offset: int

    def newlines(self) -> range:
        return range(self.new_lineno, self.new_lineno + self.new_offset)

    def dellines(self) -> range:
        return range(self.del_lineno, self.del_lineno + self.del_offset)


class ChangeKind(enum.Enum):
    ADDED = "A"
    MODIFIED = "M"
    DELETED = "D"


class Change(NamedTuple):
    filename: str
    kind: ChangeKind
    chunks: List[Chunk]

    def has_newlines(self) -> bool:
        return any(c.new_offset > 0 for c in self.chunks)

    def has_dellines(self) -> bool:
        return any(c.del_offset > 0 for c in self.chunks)

    def newlines(self) -> Iterator[int]:
        return it.chain.from_iterable((c.newlines() for c in self.chunks))

    def dellines(self) -> Iterator[int]:
        return it.chain.from_iterable((c.dellines() for c in self.chunks))


class Commit(NamedTuple):
    hash: str
    changes: List[Change]
