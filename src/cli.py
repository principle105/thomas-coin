import typer
from typer.colors import BRIGHT_YELLOW, BRIGHT_BLUE
from wallet import Wallet
from node import Node

app = typer.Typer()

@app.command()
def wallet():

    secret = input("Wallet secret: ")
    if not secret:
        secret = None

    wallet = Wallet(secret=secret)
    typer.secho(f"ADDRESS: {wallet.address}", fg=BRIGHT_BLUE)
    typer.secho(f"PRIVATE KEY: {wallet.private_key}", fg=BRIGHT_YELLOW)


@app.command()
def node():
    host = input("Host: ") or "127.0.0.1"
    port = int(input("Port: ") or 3000)

    node = Node(host, port)

    node.start()

    host = input("Host: ") or "127.0.0.1"
    port = int(input("Port: ") or 3000)
    node.connect_to_node(host, port)

if __name__ == "__main__":
    app()
