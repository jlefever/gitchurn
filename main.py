import subprocess as sp
import json
import functools

import gitparser
import ir
from typing import NamedTuple, Dict
from collections import defaultdict
from datetime import datetime


class Tag(NamedTuple):
    path: str
    name: str
    kind: str
    scope: str
    scope_kind: str

    def __str__(self):
        return "{} > {} ({})".format(self.path, self.name, self.kind)


class RawCTag:
    def __init__(self, json_text: str):
        self.json = json_text
        obj = json.loads(json_text)
        self.name = obj["name"]
        self.path = obj["path"]
        self.line = obj["line"]
        self.end = obj.get("end")
        self.kind = obj["kind"]
        self.scope = obj.get("scope")
        self.scope_kind = obj.get("scopeKind")

    def has_lineno(self, lineno: int):
        return lineno >= self.line and (self.end is None or lineno <= self.end)

    def tag(self):
        return Tag(self.path, self.name, self.kind, self.scope, self.scope_kind)

    def __str__(self):
        return "{}[{}:{}] > {} ({})".format(
            self.path, self.line, self.end, self.name, self.kind
        )


def git_show(repo: str, hash: str, filename: str):
    result = sp.run(
        ["git", "-C", repo, "show", "{}:{}".format(hash, filename)],
        encoding="UTF-8",
        capture_output=True,
        check=True,
    )
    return result.stdout


def git_files(repo: str, ref: str):
    args = ["git", "-C", repo, "ls-tree", "-r", "--name-only", ref]
    result = sp.run(args, encoding="UTF-8", capture_output=True, check=True)
    return result.stdout.splitlines()


# def git_show_parent(repo: str, hash: str, filename: str):
#     return git_show(repo, "{}^".format(hash), filename)


def get_ctags_for_text(filename: str, text: str):
    # ctags --_interactive --fields=*
    proc = sp.Popen(
#        ["ctags", "--_interactive", "--fields=NFenspk", "--extras=f"],
        ["ctags", "--_interactive", "--fields=*", "--extras=f"],
        encoding="UTF-8",
        stdout=sp.PIPE,
        stdin=sp.PIPE,
    )
    stdin = '{{"command":"generate-tags", "filename":"{}", "size": {}}}\n{}'.format(
        filename, len(text.encode("UTF-8")), text
    )
    lines = proc.communicate(stdin)[0].splitlines()[1:-1]
    return [RawCTag(l) for l in lines]


@functools.lru_cache(maxsize=None)
def get_ctags(repo: str, filename: str, hash: str):
    ctags = get_ctags_for_text(filename, git_show(repo, hash, filename))
    return ctags


@functools.lru_cache(maxsize=None)
def git_canonical(repo: str, filename: str, hash: str):
    args = ["git", "-C", repo, "rev-list", "-1", hash, "--", filename]
    result = sp.run(args, encoding="UTF-8", capture_output=True, check=True)
    return result.stdout.strip()


def get_parent_ctags(repo: str, filename: str, hash: str):
    canonical_hash = git_canonical(repo, filename, "{}^".format(hash))
    return get_ctags(repo, filename, canonical_hash)


if __name__ == "__main__":
    start = datetime.now()

    files = git_files("repo", "HEAD")
    files = (f for f in files if f.endswith(".java"))
    files = set(f for f in files if "/src/test/" not in f)
    churn: Dict[Tag, int] = defaultdict(int)

    proc = sp.Popen(
        ["git", "-C", "repo", "log", "-n", "500"] + gitparser.GIT_LOG_ARGS,
        encoding="UTF-8",
        stdout=sp.PIPE,
    )

    kinds = set()

    for commit in gitparser.parse(proc.stdout):
        for change in commit.changes:
            if change.filename not in files:
                continue
            has_news = any(c.new_offset > 0 for c in change.chunks)
            has_dels = any(c.del_offset > 0 for c in change.chunks)
            if has_news:
                new_ctags = get_ctags("repo", change.filename, commit.hash)
            if has_dels:
                del_ctags = get_parent_ctags("repo", change.filename, commit.hash)
            adds: Dict[Tag, int] = defaultdict(int)
            dels: Dict[Tag, int] = defaultdict(int)

            # hack
            json_strs: Dict[Tag, str] = dict()

            for chunk in change.chunks:
                for i in range(chunk.del_lineno, chunk.del_lineno + chunk.del_offset):
                    for ctag in del_ctags:
                        if ctag.has_lineno(i):
                            tag = ctag.tag()
                            json_strs[tag] = ctag.json
                            dels[tag] += 1
                            churn[tag] += 1
                for i in range(chunk.new_lineno, chunk.new_lineno + chunk.new_offset):
                    for ctag in new_ctags:
                        if ctag.has_lineno(i):
                            tag = ctag.tag()
                            json_strs[tag] = ctag.json
                            adds[tag] += 1
                            churn[tag] += 1

            for tag in adds.keys() | dels.keys():
                print("{}\t{}\t{}\t{}".format(commit.hash, adds[tag], dels[tag], json_strs[tag]))
                kinds.add(tag.kind)

    for kind in sorted(kinds):
        print(kind)
    # print(len(churn))

    

    # for tag in sorted(churn, key=lambda x: x.path):
    #     print("{}: {}".format(tag, churn[tag]))

    print(datetime.now() - start)
