"""fairhaven-tax CLI. Thin wrapper composing package functions."""
import typer

app = typer.Typer(help="Fair Haven Tax Assessment Analysis pipeline")


@app.command()
def version() -> None:
    """Print package version."""
    from fairhaven_tax import __version__
    typer.echo(__version__)


if __name__ == "__main__":
    app()
