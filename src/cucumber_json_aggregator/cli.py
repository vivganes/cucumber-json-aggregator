"""Command line interface."""

import json
import sys
from pathlib import Path
from typing import Annotated, NoReturn, Optional

import typer

from . import __version__
from .loader import expand_inputs, load_files
from .merge import aggregate
from .models import DedupePolicy, Strategy
from .summary import format_summary, summarize

app = typer.Typer(
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
    help="Aggregate multiple Cucumber JSON reports into a single report.",
)


def _fail(message: str, code: int) -> NoReturn:
    typer.echo(f"error: {message}", err=True)
    raise typer.Exit(code)


def _version(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.command()
def main(
    inputs: Annotated[
        Optional[list[str]],
        typer.Argument(help="Files, glob patterns, or directories (scanned recursively)."),
    ] = None,
    out: Annotated[
        Optional[Path], typer.Option("--out", "-o", help="Write to this file instead of stdout.")
    ] = None,
    strategy: Annotated[Strategy, typer.Option(help="How to combine reports.")] = Strategy.merge,
    dedupe_policy: Annotated[
        DedupePolicy, typer.Option(help="Winner among duplicate scenarios (dedupe strategy).")
    ] = DedupePolicy.last,
    indent: Annotated[
        Optional[int], typer.Option(min=0, help="Indentation width (default 2).")
    ] = None,
    compact: Annotated[bool, typer.Option(help="Write minified JSON.")] = False,
    strict: Annotated[bool, typer.Option(help="Treat any warning as a failure (exit 1).")] = False,
    quiet: Annotated[bool, typer.Option(help="Suppress the summary on stderr.")] = False,
    version: Annotated[
        bool,
        typer.Option("--version", callback=_version, is_eager=True, help="Show version and exit."),
    ] = False,
) -> None:
    if not inputs:
        _fail("no inputs given (see --help)", 2)
    if compact and indent is not None:
        _fail("--indent and --compact are mutually exclusive", 2)

    paths, warnings = expand_inputs(inputs)
    if not paths:
        for warning in warnings:
            typer.echo(f"warning: {warning}", err=True)
        _fail("no input files matched", 2)

    if out is not None:
        resolved_out = out.resolve()
        for path in paths:
            if path.resolve() == resolved_out:
                _fail(f"input '{path}' is the same as the output file; refusing to overwrite", 2)

    loaded = load_files(paths)
    warnings.extend(loaded.warnings)
    for warning in warnings:
        typer.echo(f"warning: {warning}", err=True)
    if strict and warnings:
        _fail(f"{len(warnings)} warning(s) in --strict mode; no output written", 1)

    result = aggregate([f.features for f in loaded.files], strategy, dedupe_policy)

    if compact:
        text = json.dumps(result.features, ensure_ascii=False, separators=(",", ":"))
    else:
        text = json.dumps(
            result.features, ensure_ascii=False, indent=2 if indent is None else indent
        )
    data = (text + "\n").encode("utf-8")
    if out is not None:
        try:
            out.write_bytes(data)
        except OSError as exc:
            _fail(f"cannot write '{out}': {exc.strerror or exc}", 1)
    else:
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()

    if not quiet:
        summary = summarize(
            result.features, len(loaded.files), loaded.skipped, result.duplicates_removed
        )
        typer.echo(format_summary(summary), err=True)
