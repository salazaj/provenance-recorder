from __future__ import annotations
from pathlib import Path
from .initcmd import init_project
from typing import List, Optional

from .record import record_run


import typer
from rich.console import Console

app = typer.Typer(
    help="Record and compare provenance of analysis runs.",
    no_args_is_help=True,  # makes `prov` show help instead of error
)

console = Console()


@app.callback(invoke_without_command=True)
def main() -> None:
    """
    Provenance Recorder: record what inputs, code, environment, and parameters
    produced outputs — and diff two runs.
    """
    # Nothing needed here; exists so Typer always has a root command context.
    return


@app.command()
def version() -> None:
    """Print version and exit."""
    # Keep it simple for now. We can wire this to package metadata later.
    console.print("provenance-recorder 0.1.0")


@app.command()
def init(
    prov_dir: Path = typer.Option(
        Path(".prov"), "--prov-dir", help="Where to store provenance artifacts."
    ),
    force: bool = typer.Option(
        False, "--force", help="Allow init even if prov dir exists."
    ),
    no_config: bool = typer.Option(
        False, "--no-config", help="Do not create a default config.yaml."
    ),
) -> None:
    """Initialize a .prov directory and defaults in the current project."""
    init_project(prov_dir=prov_dir, force=force, write_config=(not no_config))


@app.command()
def record(
    name: str = typer.Option(..., "--name", help="Short name for this run."),
    inputs: List[Path] = typer.Option(
        ..., "--inputs", help="Input files or directories."
    ),
    outputs: List[Path] = typer.Option(
        ..., "--outputs", help="Output files or directories."
    ),
    params: Optional[Path] = typer.Option(
        None, "--params", help="Params file (YAML/JSON)."
    ),
    prov_dir: Path = typer.Option(
        Path(".prov"), "--prov-dir", help="Provenance directory."
    ),
) -> None:
    """Record provenance after an analysis has been run."""
    record_run(
        name=name,
        inputs=inputs,
        outputs=outputs,
        params=params,
        prov_dir=prov_dir,
    )


if __name__ == "__main__":
    app()
