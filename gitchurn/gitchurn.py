# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
import subprocess as sp
from functools import reduce
from itertools import chain
from typing import Counter, FrozenSet, Iterator, List, Mapping, Tuple

from gitchurn import gitparser, ir

ENCODING = "UTF-8"

Tag = Mapping[str, str]
CanonTag = FrozenSet[Tuple[str, str]]


def has_lineno(tag: Tag, lineno: int) -> bool:
    line = tag.get("line")
    end = tag.get("end")
    if line is None:
        raise RuntimeError("Tag produced by ctags is missing `line` property.")
    # Sometimes `end` is missing. This seems like a bug with universal-ctags.
    # It seems this only happens for the last tag in the file.
    return lineno >= int(line) and (end is None or lineno <= int(end))


def count_linenos(tag: Tag, linenos: Iterator[int]) -> int:
    return sum(1 for i in linenos if has_lineno(tag, i))


def to_canon(tag: Tag) -> CanonTag:
    return frozenset((k, v) for k, v in tag.items() if k not in ["line", "end"])


def to_json(tag: CanonTag) -> str:
    return json.dumps({k: v for k, v in tag})


def to_display_name(tag: CanonTag) -> str:
    d = {k: v for k, v in tag}
    return "{} > {} ({})".format(d["path"], d["name"], d["kind"])


def run(args: List[str]) -> str:
    return sp.run(args, encoding=ENCODING, capture_output=True, check=True).stdout


class GitDriver:
    def __init__(self, **kwargs: str) -> None:
        git_bin = kwargs.get("git_bin", "git")
        git_repo = kwargs.get("git_repo", ".")
        self._init_args = [git_bin, "-C", git_repo]

    def show(self, filename: str, hash: str) -> str:
        args = self._init_args + ["show", "{}:{}".format(hash, filename)]
        return run(args)

    def files(self, ref: str) -> List[str]:
        args = self._init_args + ["ls-tree", "-r", "--name-only", ref]
        return run(args).splitlines()

    def log(self) -> Iterator[str]:
        args = self._init_args + ["log"] + gitparser.GIT_LOG_ARGS
        proc = sp.Popen(args, encoding=ENCODING, stdout=sp.PIPE)
        assert proc.stdout is not None
        return proc.stdout


class CTagsDriver:
    def __init__(self, **kwargs: str) -> None:
        self._init_args = [kwargs.get("ctags_bin", "ctags")]

    def generate_tags(self, filename: str, text: str) -> List[Tag]:
        args = self._init_args + ["--_interactive", "--fields=*"]
        proc = sp.Popen(args, encoding=ENCODING, stdout=sp.PIPE, stdin=sp.PIPE)
        cin = '{{"command":"generate-tags", "filename":"{}", "size":{}}}\n{}'.format(
            filename, len(text.encode(ENCODING)), text
        )
        # We skip the first and last message because they are not tags.
        lines = proc.communicate(cin)[0].splitlines()[1:-1]
        return [json.loads(line) for line in lines]


class TagProvider:
    def __init__(self, git: GitDriver, ctags: CTagsDriver):
        self._git = git
        self._ctags = ctags

    def get_tags(self, filename: str, hash: str) -> List[Tag]:
        return self._ctags.generate_tags(filename, self._git.show(filename, hash))

    def get_parent_tags(self, filename: str, hash: str) -> List[Tag]:
        return self.get_tags(filename, "{}^".format(hash))


class ChurnProvider:
    def __init__(self, tag_provider: TagProvider):
        self._tag_provider = tag_provider

    def get_churn(self, commit: ir.Commit) -> Counter[CanonTag]:
        adds = (self.get_adds(commit.hash, c) for c in commit.changes)
        dels = (self.get_dels(commit.hash, c) for c in commit.changes)
        return reduce(lambda a, b: a + b, chain(adds, dels), Counter())

    def get_adds(self, hash: str, change: ir.Change) -> Counter[CanonTag]:
        count: Counter[CanonTag] = Counter()
        if not change.has_newlines():
            return count
        for tag in self._tag_provider.get_tags(change.filename, hash):
            count[to_canon(tag)] = count_linenos(tag, change.newlines())
        return count

    def get_dels(self, hash: str, change: ir.Change) -> Counter[CanonTag]:
        count: Counter[CanonTag] = Counter()
        if not change.has_dellines():
            return count
        for tag in self._tag_provider.get_parent_tags(change.filename, hash):
            count[to_canon(tag)] = count_linenos(tag, change.dellines())
        return count