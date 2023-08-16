"""Update requirements added as submodules."""

from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from dulwich.porcelain import submodule_list, get_branch_remote
from dulwich.repo import Repo

from re import MULTILINE, VERBOSE, Pattern, compile

REPLACEMENTS = {
    compile(
        flags=VERBOSE | MULTILINE,
        pattern=r"""
        ^                                      # Start of line
        (?P<prefix>\s*['"])?                   # Optional `"` as in pyproject.toml
        (?P<name>\w+)@                         # name@
        (?P<domain>git\+https://github\.com/)  # git+https://github.com/
        (?P<org>\w+/)                          # org/
        (?P=name)@                             # name@
        (?P<commit>\w+)                        # <commit-hash>
        (?P<suffix>['"],)?                     # Optional `",` as in pyproject.toml
        $                                      # End of line
        """,
    ): lambda commit: rf"\g<prefix>\g<name>@\g<domain>\g<org>\g<name>@{commit}\g<suffix>"
}


def main():
    with closing(repo := Repo(str(Path.cwd()))):
        submodules = [Submodule(*item) for item in list(submodule_list(repo))]
    requirements_files = [Path("pyproject.toml")] + sorted(
        Path(".tools/requirements").glob("requirements*.txt")
    )
    for submodule in submodules:
        for file in requirements_files:
            for pattern, repl in REPLACEMENTS.items():
                file.write_text(
                    encoding="utf-8",
                    data=pattern.sub(
                        repl=repl(submodule.commit), string=file.read_text("utf-8")
                    ),
                )


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


if __name__ == "__main__":
    main()
