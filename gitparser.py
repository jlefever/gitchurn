import datetime
import re
from typing import List, Optional

import ir

RE_CHUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

STR_COMMIT = "commit "
STR_DIFF = "diff --git"
STR_FROM = "--- a/"
STR_TO = "+++ b/"
STR_CHUNK = "@@ -"

GIT_LOG_ARGS = [
    # Format commits so the output log can be parsed.
    "--pretty=short",
    "--no-decorate",
    # Order commits so a parent always appears before its children.
    "--topo-order",
    "--reverse",
    # Disable rename and move detection.
    "--no-renames",
    "--no-color-moved",
    # Each commit includes the hashs of its parent(s). This enables
    # parent rewriting by default.
    "--parents",
    # Disable parent rewriting.
    "--full-history",
    # Display patch information with each commit.
    "-U0",
    "--histogram",
    # Only show Added (A), Deleted (D), and Modified (M) files.
    "--diff-filter=ADM",
    "--no-merges"
]


def _iso_date(text: str):
    return datetime.datetime.strptime(text, r"%Y-%m-%d %H:%M:%S %z")


class _ParserState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.hash: Optional[str] = None
        self.parents: List[str] = list()
        self.changes: List[ir.Change] = list()
        self.filename: Optional[str] = None
        self.change_kind: ir.ChangeKind = ir.ChangeKind.MODIFIED
        self.chunks: List[ir.Chunk] = list()


def parse(lines):
    state = _ParserState()

    def push_change(state: _ParserState):
        if state.filename is not None:
            change = ir.Change(state.filename, state.change_kind, state.chunks)
            state.changes.append(change)
        state.filename = None
        state.change_kind = ir.ChangeKind.MODIFIED
        state.chunks = list()

    def push_commit(state: _ParserState):
        commit = ir.Commit(state.hash, state.parents, state.changes)
        state.reset()
        return commit

    for line in lines:
        line = line.rstrip()
        if line.startswith(STR_COMMIT):
            if state.hash is not None:
                push_change(state)
                yield push_commit(state)
            hashs = line[len(STR_COMMIT) :].split(" ")
            state.hash = hashs[0]
            state.parents = hashs[1:]
        elif line.startswith(STR_DIFF):
            push_change(state)
        elif line.startswith(STR_FROM):
            text = line[len(STR_FROM) :].strip()
            state.change_kind = ir.ChangeKind.DELETED
            state.filename = text
        elif line.startswith(STR_TO):
            if state.filename is None:
                state.change_kind = ir.ChangeKind.ADDED
            else:
                state.change_kind = ir.ChangeKind.MODIFIED
            text = line[len(STR_TO) :].strip()
            assert (state.filename is None) or (state.filename == text)
            state.filename = text
        elif line.startswith(STR_CHUNK):
            match = RE_CHUNK.match(line)
            assert match is not None
            a, b, c, d = match.groups()
            del_lineno = int(a)
            del_offset = int(b) if b else 1
            new_lineno = int(c)
            new_offset = int(d) if d else 1
            chunk = ir.Chunk(new_lineno, new_offset, del_lineno, del_offset)
            state.chunks.append(chunk)
    if state.hash is not None:
        push_change(state)
        yield push_commit(state)

    # filename = "gitlog.txt"
    # with codecs.open(filename, "r", encoding="iso-8859-1") as file:
    #     print(next(parse(file)))
    #     print(next(parse(file)))
