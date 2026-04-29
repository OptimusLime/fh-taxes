"""fairhaven-tax CLI. Thin wrapper composing package functions."""
import subprocess
import sys

import typer

app = typer.Typer(help="Fair Haven Tax Assessment Analysis pipeline")


@app.command()
def version() -> None:
    """Print package version."""
    from fairhaven_tax import __version__
    typer.echo(__version__)


@app.command()
def ingest() -> None:
    """Run full ingest: njgin -> dlgs -> sr1a -> reconcile."""
    scripts = [
        "scripts/ingest_njgin.py",
        "scripts/extract_dlgs.py",
        "scripts/ingest_sr1a.py",
        "scripts/reconcile.py",
    ]
    for s in scripts:
        rc = subprocess.call([sys.executable, s])
        if rc != 0:
            raise typer.Exit(rc)


@app.command()
def validate() -> None:
    """Run Phase 1 validation gate (D-09)."""
    rc = subprocess.call([sys.executable, "scripts/validate_phase1.py"])
    raise typer.Exit(rc)


if __name__ == "__main__":
    app()
