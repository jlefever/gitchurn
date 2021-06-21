# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import argparse
import sys
from datetime import datetime
from typing import List, Optional

from gitchurn import gitchurn, gitparser


def main(argv: Optional[List[str]] = None):
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser(
        description="calculate change churn below the file-level"
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
        help="any additional arguments to pass to git-log (optional)",
    )
    parser.add_argument(
        "--max-changes",
        dest="max_changes",
        help="exclude commits that changed more than this number of files (optional)",
    )

    args = parser.parse_args(argv)
    git_driver = gitchurn.GitDriver(
        git_bin=args.git_bin, git_repo=args.git_repo, git_log_args=args.git_log_args
    )
    ctags_driver = gitchurn.CTagsDriver(ctags_bin=args.ctags_bin)
    tag_provider = gitchurn.TagProvider(git_driver, ctags_driver)
    churn_provider = gitchurn.ChurnProvider(tag_provider)
    printer = gitchurn.ChurnPrinter(churn_provider, git_driver)

    start = datetime.now()
    printer.print(int(args.max_changes))
    print(datetime.now() - start)
    return 0


if __name__ == "__main__":
    sys.exit(main())
