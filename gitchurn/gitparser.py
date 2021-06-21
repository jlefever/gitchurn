# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import re
from typing import Iterator, List, Optional

from gitchurn import ir

STR_COMMIT = "commit "
STR_DIFF = "diff --git"
STR_NEW_FILE = "new file mode"
STR_DEL_FILE = "deleted file mode"
STR_FROM = "--- a/"
STR_TO = "+++ b/"
STR_CHUNK = "@@ -"

RE_CHUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

GIT_LOG_ARGS = [
    # Format commits so the output log can be parsed.
    "--pretty=short",
    "--no-decorate",
    # Disable rename and move detection.
    "--no-renames",
    "--no-color-moved",
    # Display patch information with each commit and show only changed lines.
    "--unified=0",
    # Use the histogram algorithm for diffs. This is best for source code.
    # https://link.springer.com/article/10.1007/s10664-019-09772-z
    "--histogram",
    # Only show Added (A), Deleted (D), and Modified (M) files.
    "--diff-filter=ADM",
    # Hide merge commits.
    "--no-merges"
]


class ChangeBuilder:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._filename: Optional[str] = None
        self._kind: ir.ChangeKind = ir.ChangeKind.MODIFIED
        self._chunks: List[ir.Chunk] = []

    def set_filename(self, filename: str) -> None:
        self._filename = filename

    def set_kind(self, kind: ir.ChangeKind) -> None:
        self._kind = kind

    def add_chunk(self, chunk: ir.Chunk) -> None:
        self._chunks.append(chunk)

    def is_valid(self) -> bool:
        return self._filename is not None

    def finalize(self) -> ir.Change:
        if self._filename is None:
            raise RuntimeError("Cannot finalize change without a filename.")
        change = ir.Change(self._filename, self._kind, self._chunks)
        self.reset()
        return change


class CommitBuilder:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._hash: Optional[str] = None
        self._changes: List[ir.Change] = []

    def set_hash(self, hash: str) -> None:
        self._hash = hash

    def add_change(self, change: ir.Change) -> None:
        self._changes.append(change)

    def is_valid(self) -> bool:
        return self._hash is not None

    def finalize(self) -> ir.Commit:
        if self._hash is None:
            raise RuntimeError("Cannot finalize commit without a hash.")
        commit = ir.Commit(self._hash, self._changes)
        self.reset()
        return commit


def parse_chunk(text: str) -> ir.Chunk:
    match = RE_CHUNK.match(text)
    if match is None:
        raise RuntimeError("Invalid chunk header: {}".format(text))
    a, b, c, d = match.groups()
    del_offset = int(b) if b else 1
    new_offset = int(d) if d else 1
    return ir.Chunk(int(c), new_offset, int(a), del_offset)


def parse(lines: Iterator[str]) -> Iterator[ir.Commit]:
    # These builders hold our intermediate state.
    commit_builder = CommitBuilder()
    change_builder = ChangeBuilder()

    # Iterate line by line through the log.
    for line in (l.rstrip() for l in lines):
        if line.startswith(STR_COMMIT):
            # Yield the previous commit before starting a new one.
            if change_builder.is_valid():
                commit_builder.add_change(change_builder.finalize())
            if commit_builder.is_valid():
                yield commit_builder.finalize()
            # Set the hash.
            commit_builder.set_hash(line[len(STR_COMMIT) :])
        # Finalize the current change before starting a new one.
        elif line.startswith(STR_DIFF) and change_builder.is_valid():
            commit_builder.add_change(change_builder.finalize())
        # Below here we just update our intermediate state.
        elif line.startswith(STR_FROM):
            change_builder.set_filename(line[len(STR_FROM) :])
        elif line.startswith(STR_TO):
            change_builder.set_filename(line[len(STR_TO) :])
        elif line.startswith(STR_NEW_FILE):
            change_builder.set_kind(ir.ChangeKind.ADDED)
        elif line.startswith(STR_DEL_FILE):
            change_builder.set_kind(ir.ChangeKind.DELETED)
        elif line.startswith(STR_CHUNK):
            change_builder.add_chunk(parse_chunk(line))

    # Yield the last commit. (Except when the log file is empty.)
    if change_builder.is_valid():
        commit_builder.add_change(change_builder.finalize())
    if commit_builder.is_valid():
        yield commit_builder.finalize()
