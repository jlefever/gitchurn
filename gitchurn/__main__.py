# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import argparse
import sys
from typing import List, Optional

from gitchurn import gitchurn


def main(argv: Optional[List[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="gitchurn", description="calculate change churn below the file-level"
    )
    parser.add_argument(
        "--git-repo",
        dest="git_repo",
        default=".",
        help="path to the git repository (default: current directory)",
    )
    parser.add_argument(
        "--git-path",
        dest="git_bin",
        default="git",
        help="path to git binary (default: git)",
    )
    parser.add_argument(
        "--ctags-path",
        dest="ctags_bin",
        default="ctags",
        help="path to the universal-ctags binary (default: ctags)",
    )
    parser.add_argument(
        "--git-log-args",
        dest="git_log_args",
        default="",
        help="any additional arguments to pass to git-log (optional)",
    )
    parser.add_argument(
        "--max-changes",
        dest="max_changes",
        help="exclude commits that changed more than this number of files (optional)",
    )

    formatter_factory = gitchurn.TagFormatterFactory()

    parser.add_argument(
        "--tag-format",
        choices=formatter_factory.kinds(),
        default="human",
        dest="tag_format",
        help="how to display the tags (default: human)",
    )

    args = parser.parse_args(argv)
    git_driver = gitchurn.GitDriver(
        git_bin=args.git_bin, git_repo=args.git_repo, git_log_args=args.git_log_args
    )
    ctags_driver = gitchurn.CTagsDriver(ctags_bin=args.ctags_bin)
    tag_provider = gitchurn.TagProvider(git_driver, ctags_driver)
    churn_provider = gitchurn.ChurnProvider(tag_provider)
    record_provider = gitchurn.LogRecordProvider(churn_provider, git_driver)

    max_changes = int(args.max_changes) if args.max_changes else None
    formatter = formatter_factory.create(args.tag_format)
    for record in record_provider.fetch(formatter, max_changes):
        print("{}\t{}\t{}".format(record.commit, record.churn, record.tag))
    return 0


if __name__ == "__main__":
    sys.exit(main())
