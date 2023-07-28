"""Update DVC paths (implicitly through import of PARAMS) and build docs."""

import asyncio
from asyncio import TaskGroup, create_subprocess_exec
from asyncio.subprocess import PIPE
from collections.abc import Callable, Coroutine
from concurrent.futures import ProcessPoolExecutor
from contextlib import AbstractContextManager
from functools import wraps
from itertools import chain
from os import chdir
from pathlib import Path
from shlex import quote, split
from subprocess import CalledProcessError
from sys import stdout
from typing import Any

from dulwich.porcelain import status
from dulwich.repo import Repo  # type: ignore  # pyright: 1.1.317
from loguru import logger  # type: ignore  # pyright: 1.1.317
from ploomber_engine import execute_notebook  # type: ignore  # pyright: 1.1.317

# Pipeline parameters
REPO = Repo("")
NOTEBOOKS = Path("notebooks")
IPYNB = NOTEBOOKS / "ipynb"
HTML = NOTEBOOKS / "html"
MD = NOTEBOOKS / "md"
DOCX = NOTEBOOKS / "docx"
SCRIPTS = Path("scripts")
TEMPLATE = SCRIPTS / "template.py"
CSL = SCRIPTS / "international-journal-of-heat-and-mass-transfer.csl"
ZOTERO = SCRIPTS / "zotero.lua"
ALSO_COMMITTED = False
MODIFIED_ONLY = CLEAN = EXECUTE = EXPORT = REPORT = COMMIT = True

# Notebook parameter overrides
OVERRIDE = RELINK = False

# Logging
VERBOSE_LOG = True
REPLAY = LOG_TO_FILE = False
logger.remove()
for sink in (["pre_repro.log"] if LOG_TO_FILE else []) + ([] if REPLAY else [stdout]):
    logger.add(
        sink=sink, enqueue=True, format=("<green>{time:mm:ss}</green> | {message}")
    )
logger = logger.opt(colors=not REPLAY)
logger.info("<yellow>START</yellow> pre_repro")
if not VERBOSE_LOG:
    logger.disable("__main__")


async def main():
    nbs = get_nbs(REPO, IPYNB, MODIFIED_ONLY)
    if not nbs:
        return
    if CLEAN:
        await clean(nbs)
        nbs = get_nbs(REPO, IPYNB, MODIFIED_ONLY)
        if not nbs:
            return
    for process, cond in {execute: EXECUTE, export: EXPORT, report: REPORT}.items():
        if cond:
            await process(nbs)


# * -------------------------------------------------------------------------------- * #
# * NOTEBOOK PROCESSING


def get_nbs(repo: Repo, docs: Path, modified_only: bool) -> dict[Path, str]:
    """Get all notebooks or just the modified ones."""
    return (
        fold_modified_nbs(repo, docs)
        if modified_only
        else fold_docs_nbs(list(docs.glob("**/*.ipynb")), docs)
    )


async def clean(nbs):
    """Clean notebooks."""
    logger.info("<yellow>START</yellow> CLEAN")
    async with TaskGroup() as tg:
        for nb in nbs.values():
            tg.create_task(clean_notebook(nb, lint=True))
    logger.info("<green>FINISH</green> CLEAN")


async def execute(nbs: dict[Path, str]):
    """Execute notebooks."""
    logger.info("<yellow>START</yellow> EXECUTE")
    with ProcessPoolExecutor() as executor:
        for nb in nbs:
            executor.submit(
                execute_notebook,
                input_path=nb,
                output_path=nb,
                progress_bar=VERBOSE_LOG,
                remove_tagged_cells=["ploomber-engine-error-cell"],
                parameters=dict(RELINK=RELINK) if OVERRIDE else {},
            )
    logger.info("<green>FINISH</green> EXECUTE")
    logger.info("<yellow>START</yellow> REMOVE EXECUTION METADATA")
    async with TaskGroup() as tg:
        for nb in nbs.values():
            tg.create_task(clean_notebook(nb, lint=False))
    logger.info("<green>FINISH</green> REMOVE EXECUTION METADATA")


async def export(nbs: dict[Path, str]):
    """Export notebooks to Markdown and HTML."""
    logger.info("<yellow>START</yellow> EXPORT")
    async with TaskGroup() as tg:
        for nb in nbs.values():
            tg.create_task(export_notebook(nb, html=fold(HTML), md=fold(MD)))
    logger.info("<green>FINISH</green> EXPORT")


async def report(nbs: dict[Path, str]):
    """Generate DOCX reports."""
    logger.info("<yellow>START</yellow> REPORT")
    async with TaskGroup() as tg:
        for nb in nbs:
            tg.create_task(
                report_on_notebook(
                    **{
                        kwarg: fold(path)
                        for kwarg, path in dict(
                            workdir=MD,
                            template=TEMPLATE,
                            zotero=ZOTERO,
                            csl=CSL,
                            docx=DOCX / nb.with_suffix(".docx").name,
                            md=MD / nb.with_suffix(".md").name,
                        ).items()
                    }
                )
            )
    logger.info("<green>FINISH</green> REPORT")


# * -------------------------------------------------------------------------------- * #
# * SINGLE NOTEBOOK PROCESSING


async def clean_notebook(nb: str, lint: bool):
    """Clean a notebook."""
    commands = [f"nbqa black {nb}", f"nbqa ruff --fix-only {nb}"] if lint else []
    commands.append(
        "   nb-clean clean --remove-empty-cells"
        "     --preserve-cell-outputs"
        "     --preserve-cell-metadata special tags"
        f"    -- {nb}"
    )
    for command in commands:
        await run_process(command)


async def export_notebook(nb: str, md: str, html: str):
    """Export a notebook to Markdown and HTML."""
    for command in [
        f"jupyter-nbconvert --to markdown --no-input --output-dir {md} {nb}",
        f"jupyter-nbconvert --to html --no-input --output-dir {html} {nb}",
    ]:
        await run_process(command)


def preserve_dir(f: Callable[..., Coroutine[Any, Any, Any]]):
    """Preserve the current directory."""

    @wraps(f)
    async def wrapped(*args, **kwargs):
        return await CoroWrapper(f(*args, **kwargs), PreserveDir())

    return wrapped


@preserve_dir
async def report_on_notebook(
    workdir: str, template: str, zotero: str, csl: str, docx: str, md: str
):
    """Generate a DOCX report from a notebook.

    Requires changing the active directory to the Markdown folder outside of this
    asynchronous function, due to how Pandoc generates links inside the documents.
    """
    chdir(workdir)
    await run_process(
        venv=False,
        command=(
            " pandoc"
            # Pandoc configuration
            "   --standalone"  # Don't produce a document fragment.
            "   --from markdown-auto_identifiers"  # Avoids bookmark pollution around Markdown headers
            "   --to docx"  # The output format
            f"  --reference-doc {template}"  # The template to export literature reviews to
            # Zotero Lua filter and metadata passed to it
            f"  --lua-filter {zotero}"  # Needs to be the one downloaded from the tutorial page https://retorque.re/zotero-better-bibtex/exporting/pandoc/#from-markdown-to-zotero-live-citations
            "   --metadata zotero_library:3"  # Corresponds to "Nucleate pool boiling [3]"
            f"  --metadata zotero_csl_style:{csl}"  # Must also be installed in Zotero
            # I/O
            f"  --output {docx}"
            f"  {md}"
        ),
    )


# * -------------------------------------------------------------------------------- * #
# * UTILITIES

COLORS = {
    "jupyter-nbconvert": "blue",
    "nb-clean": "magenta",
    "nbqa": "cyan",
    "pandoc": "red",
}


async def run_process(command: str, venv: bool = True):
    """Run a subprocess asynchronously."""
    command, *args = split(command, posix=False)

    # Log start
    file = args[-1].split("/")[-1]
    colored_command = f"<{COLORS[command]}>{command}</{COLORS[command]}>"
    logger.info(f"    <yellow>Start </yellow> {colored_command} {file}")

    # Run process
    process = await create_subprocess_exec(
        f"{'.venv/scripts/' if venv else ''}{command}", *args, stdout=PIPE, stderr=PIPE
    )
    stdout, stderr = (msg.decode("utf-8") for msg in await process.communicate())
    message = (
        (f"{stdout}\n{stderr}" if stdout and stderr else stdout or stderr)
        .replace("\r\n", "\n")
        .strip()
    )

    # Handle exceptions
    if process.returncode:
        exception = CalledProcessError(
            returncode=process.returncode,
            cmd=command,
            output=stdout,
            stderr=stderr,
        )
        exception.add_note(message)
        exception.add_note("Arguments:\n" + "    \n".join(args))
        raise exception

    # Log finish
    logger.info(
        f"    <green>Finish</green> {colored_command} {file}"
        + ((": " + message.replace("\n", ". ")[:30] + "...") if message else "")
    )


def fold_modified_nbs(repo: Repo, docs: Path) -> dict[Path, str]:
    """Fold the paths of modified documentation notebooks."""
    modified = get_modified_files(repo)
    return fold_docs_nbs(modified, docs) if docs in modified else {}


def get_modified_files(repo: Repo) -> list[Path]:
    """Get files considered modified by DVC."""
    return [
        Path(path.decode("utf-8"))
        for path in (status(repo).unstaged + list(chain(*status(repo).staged.values())))  # type: ignore
    ]


def fold_docs_nbs(paths: list[Path], docs: Path) -> dict[Path, str]:
    """Fold the paths of documentation-related notebooks."""
    return {
        nb: fold(nb)
        for nb in sorted(
            {
                path.with_suffix(".ipynb")
                for path in paths
                # Consider notebook modified even if only its `.h5` file is
                if path.is_relative_to(docs) and path.suffix in [".ipynb", ".h5"]
            }
        )
    }


def fold(path: Path):
    """Resolve and normalize a path to a POSIX string path with forward slashes."""
    return quote(str(path.resolve()).replace("\\", "/"))


# * -------------------------------------------------------------------------------- * #
# * PRIMITIVES


class PreserveDir:
    """Re-entrant context manager that preserves the current directory.

    Reference: <https://stackoverflow.com/a/64395754/20430423>
    """

    def __init__(self):
        self.outer_dir = Path.cwd()
        self.inner_dir = None

    def __enter__(self):
        self.outer_dir = Path.cwd()
        if self.inner_dir is not None:
            chdir(self.inner_dir)

    def __exit__(self, *exception_info_):
        self.inner_dir = Path.cwd()
        chdir(self.outer_dir)


class CoroWrapper:
    """Wrap `target` to have every send issued in a `context`.

    Reference: <https://stackoverflow.com/a/56079900/1600898>
    """

    def __init__(
        self, target: Coroutine[Any, Any, Any], context: AbstractContextManager[Any]
    ):
        self.target = target
        self.context = context

    # wrap an iterator for use with 'await'
    def __await__(self):
        # unwrap the underlying iterator
        target_iter = self.target.__await__()
        # emulate 'yield from'
        iter_send, iter_throw = target_iter.send, target_iter.throw
        send, message = iter_send, None
        while True:
            # communicate with the target coroutine
            try:
                with self.context:  # type: ignore  # pyright: 1.1.311
                    signal = send(message)  # type: ignore  # pyright: 1.1.311
            except StopIteration as err:
                return err.value
            else:
                send = iter_send
            # communicate with the ambient event loop
            try:
                message = yield signal
            except BaseException as err:  # noqa: BLE001
                send, message = iter_throw, err


# * -------------------------------------------------------------------------------- * #

if __name__ == "__main__":
    asyncio.run(main())
    logger.enable("__main__")
    logger.info("<green>FINISH</green> pre_repro")
