"""Update requirements versions which are coupled to others."""

from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from re import MULTILINE, VERBOSE, Pattern, compile

from dulwich.porcelain import submodule_list
from dulwich.repo import Repo


def main():
    # Regexes to bump pandas-stubs in line with pandas
    dependency_relation = r"(?P<relation>[=~>]=)"  # ==, ~=, or >=
    pandas_re, pandas_stubs_re, pandas_repl = (
        compile_mx(
            rf"""
            pandas                  # pandas
            (\[[\w,]+\])?           # e.g. [hdf5,performance] (optional)
            {dependency_relation}   # e.g. ==
            (?P<version>[\w\d\.]*)  # e.g. 2.0.2
            """
        ),
        compile_mx(
            rf"""
            (?P<dep>pandas-stubs)   # pandas-stubs
            {dependency_relation}   # e.g. ~=
            (?P<version>[\w\d\.]*)  # e.g. 2.0.2
            """
        ),
        lambda version: rf"\g<prefix>\g<dep>\g<relation>{version}\g<suffix>",
    )

    # Regexes to bump packages which are pinned to commit hashes
    submodule_re, submodule_repl = (
        compile_mx(
            r"""
            (?P<name>\w+)@                         # name@
            (?P<domain>git\+https://github\.com/)  # git+https://github.com/
            (?P<org>\w+/)                          # org/
            (?P=name)@                             # name@
            (?P<commit>\w+)                        # <commit-hash>
            $"""
        ),
        lambda commit: (
            rf"\g<prefix>\g<name>@\g<domain>\g<org>\g<name>@{commit}\g<suffix>"
        ),
    )

    with closing(repo := Repo(str(Path.cwd()))):
        submodules = [Submodule(*item) for item in list(submodule_list(repo))]
    requirements_files = [
        Path("pyproject.toml"),
        *sorted(Path(".tools/requirements").glob("requirements*.txt")),
    ]
    for file in requirements_files:
        content = original_content = file.read_text("utf-8")
        if pandas_match := pandas_re.search(content):
            content = pandas_stubs_re.sub(
                repl=pandas_repl(pandas_match["version"]), string=content
            )
        for submodule in submodules:
            content = submodule_re.sub(
                repl=submodule_repl(submodule.commit), string=content
            )
        if content != original_content:
            file.write_text(encoding="utf-8", data=content)


@dataclass
class Submodule:
    """Represents a git submodule."""

    name: str
    """The submodule name."""
    commit: str
    """The commit hash currently tracked by the submodule."""

    def __post_init__(self):
        """Handle byte strings reported by some submodule sources, like dulwich."""
        # dulwich.porcelain.submodule_list returns bytes
        if isinstance(self.name, bytes):
            self.name = self.name.decode("utf-8")


def compile_mx(pattern: str) -> Pattern[str]:
    """Compile a verbose, multi-line regular expression pattern."""
    return compile(
        flags=VERBOSE | MULTILINE,
        pattern=rf"""^
            (?P<prefix>\s*['"])?  # Optional `"` as in pyproject.toml
            {pattern}
            (?P<suffix>['"],)?  # Optional `",` as in pyproject.toml
            $""",
    )


if __name__ == "__main__":
    main()
