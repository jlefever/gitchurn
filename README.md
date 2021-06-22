# Git Churn

The purpose of this tool is to calculate change churn below the file-level. Git can already calculate churn with `git log --numstat` which will print how many lines of text were added and removed in each file touched by a commit. This tool prints the same information for each *tag* touched by a commit. A tag is any item in a source file such as a class, function, field, etc. We detect tags using [Universal CTags](https://github.com/universal-ctags/ctags). In effect, this tool is just some glue between `ctags` and `git`.

## Install

`gitchurn` can be installed with pip.

```
pip install gitchurn
```

[Git](https://git-scm.com/) must also be installed. [Universal CTags](https://github.com/universal-ctags/ctags) is also required. Please follow the link for instructions. You can test your install by running `ctags --version`. 

## Usage

Simply navigate to a git repository and run `python -m gitchurn` or just `gitchurn`. You will see something like:

```
9d0e3d1af0cb7e62c810ec23f97e12e86ab3cf6f	14	<tag_1>
9d0e3d1af0cb7e62c810ec23f97e12e86ab3cf6f	15	<tag_2>
a058e4559d0363ed956780e81f2e6f0d84d0ead3	2	<tag_3>
```

The output is always three columns delimated by tabs. The first column is the commit hash. The second column is the churn (added plus deleted lines). The last column is the tag. By default, tags are printed in a human readable format but this can be changed with `--tag-format`. See `gitchurn --help` for further options.

These churn calculations are fairly expensive and are not going to fluxuate, so it might be wise to immediately pipe the output to a file. You will also see significant performance gains by filtering down commits. See the next section for more details.

## Example

For a more involved example, say we want the churn for the last 100 commits of some project. Let's use [Apache DeltaSpike](https://github.com/apache/deltaspike) as an example.

```
git clone https://github.com/apache/deltaspike
cd deltaspike
gitchurn --git-log-args "master -n 100"
```

The arguments passed to `--git-log-args` will be fowarded to [git-log](https://git-scm.com/docs/git-log). So `master -n 100` means we want only the 100 most recent commits reachable from the `master` branch.

Now we can limit this even further. Say we are only interested in Java code which is not tests.

```
gitchurn --git-log-args "master -n 100 -- **/*.java :^**/src/test/**"
```

Everything after `--` is interpreted as path information by git-log. So `**/*.java` is a glob telling git to only select Java files. Similarly, `:^**/src/test/**` tells git to exclude tests. (The `:^` prefix causes git to invert the selection.)

Finally, if we want to ignore large commits (such as those caused by refactoring), we can set a maximum commit size.

```
gitchurn --git-log-args "master -n 100 -- **/*.java :^**/src/test/**" --max-changes 30
```

So any commits which have changed more than 30 non-test Java files will be excluded.
