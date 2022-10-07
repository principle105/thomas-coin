import typer
import yaml
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from InquirerPy.utils import color_print
from InquirerPy.validator import EmptyInputValidator
from pyfiglet import figlet_format
from tcoin.constants import MIN_SEND_AMT
from tcoin.p2p.nodes import Node
from tcoin.tangle import Tangle
from tcoin.tangle.messages import Transaction, TransactionPayload
from tcoin.wallet import Wallet
from yaspin import yaspin
from yaspin.spinners import Spinners

# Initializing cli
app = typer.Typer()


class Send:
    @staticmethod
    def success(text: str):
        color_print([("green", text)])

    @staticmethod
    def fail(text: str):
        color_print([("red", text)])

    @staticmethod
    def primary(text: str):
        color_print([("#f6ca44", text)])

    @staticmethod
    def secondary(text: str):
        color_print([("#4470f6", text)])

    @staticmethod
    def regular(text: str):
        color_print([("", text)])

    @staticmethod
    def spinner(text: str):
        return yaspin(Spinners.moon, text=text, color="cyan", timer=True)


def handle_pk_input(secret: str):
    try:
        wallet = Wallet(secret=secret)
    except ValueError:
        Send.fail("That is not a valid private key")
        return

    return wallet


def node_stats(_, node: Node):
    Send.primary(
        f"Inbound Connections: {len(node.nodes_inbound)}\n"
        f"Outbound Connections: {len(node.nodes_outbound)}"
    )


def tangle_stats(tangle: Tangle, _):
    msg_amt = len(tangle.msgs)

    t_amt = 0
    sent = 0

    for t in tangle.msgs.values():
        if isinstance(t, Transaction):
            sent += t.get_transaction().amt
            t_amt += 1

    Send.primary(
        f"Total Messages: {msg_amt}\n"
        f"Total Transactions: {t_amt}\n"
        f"Total Sent: {sent}"
    )


def send(tangle: Tangle, node: Node):
    balance = tangle.get_balance(node.wallet.address)

    if balance < MIN_SEND_AMT:
        return Send.fail(f"You have less than the minimum send amount {MIN_SEND_AMT}")

    address = inquirer.text(
        message="Address:", validate=EmptyInputValidator()
    ).execute()

    amount = inquirer.number(
        message="Amount:",
        min_allowed=MIN_SEND_AMT,
        max_allowed=balance,
        default=None,
        validate=EmptyInputValidator(),
    ).execute()

    amount = int(amount)

    index = tangle.get_transaction_index(node.wallet.address)

    # Constructing the transaction
    payload = TransactionPayload(receiver=address, amt=amount, index=index)

    msg = node.create_message(Transaction, payload=payload.to_dict())

    msg.select_parents(tangle)

    Send.success("Message Constructed")

    proceed = inquirer.confirm(
        message=f"Are you sure you want to send {amount} coins?", default=False
    ).execute()

    if proceed is False:
        return Send.fail("Transaction cancelled!")

    with Send.spinner("Solving Proof of Work"):
        msg.do_work(tangle)

    Send.success("Proof of Work Solved")

    msg.sign(node.wallet)

    # # Checking if the message is valid
    if msg.is_valid(tangle) is False:
        return Send.fail("Invalid transaction!")

    tangle.add_msg(msg)

    with Send.spinner("Broadcasting Transaction"):
        node.send_to_nodes(msg.to_dict())

    Send.success("Transaction Broadcasted")
    Send.primary(f"Message Hash: {msg.hash}")


def connect(_, node: Node):
    host = inquirer.text(
        message="Host:",
        validate=EmptyInputValidator(),
    ).execute()

    port = inquirer.number(
        message="Port:",
        validate=EmptyInputValidator(),
    ).execute()

    port = int(port)

    node.connect_to_node(host, port)


def view_balance(tangle: Tangle, node: Node):
    address = inquirer.text(message="Address:").execute()

    if not address:
        address = node.wallet.address

    balance = tangle.get_balance(address)

    sender = Send.success if balance else Send.fail

    sender(f"Balance: {balance}")


def view_address(_, node: Node):
    Send.primary(f"Your Address: {node.wallet.address}")


def view_msg(tangle: Tangle, _):
    msg_hash = inquirer.text(
        message="Message Hash:",
        validate=EmptyInputValidator(),
    ).execute()

    msg = tangle.get_msg(msg_hash)

    if msg is None:
        return Send.fail("A message with that hash does not exist")

    formatted_data = yaml.dump(msg.to_dict())

    Send.success(f"\n{formatted_data}")


@app.command()
def start():
    host = inquirer.text(
        message="Host:",
        validate=EmptyInputValidator(),
    ).execute()

    port = inquirer.number(
        message="Port:",
        validate=EmptyInputValidator(),
    ).execute()

    port = int(port)

    pk = inquirer.secret(
        message="Your Private Key:",
        validate=EmptyInputValidator(),
    ).execute()

    wallet = handle_pk_input(pk)

    if wallet is None:
        return

    full_node = inquirer.confirm(
        message="Would you like it to be a full node?", default=False
    ).execute()

    with Send.spinner("Starting Node") as sp:
        tangle = Tangle.from_save()
        sp.write("- Loaded tangle from save")

        node = Node(
            host=host,
            port=int(port),
            tangle=tangle,
            wallet=wallet,
            full_node=full_node,
        )
        node.start()
        sp.write("- Node started")

        # Auto peering
        node.connect_to_known_nodes()

        sp.write("- Connected to the network")

        sp.ok("✔")

    choices = {
        "Connect": connect,
        "Node Stats": node_stats,
        "Tangle Stats": tangle_stats,
        "View Address": view_address,
        "Balance": view_balance,
        "Send": send,
        "View Message": view_msg,
    }

    is_done = False

    while is_done is False:
        result = inquirer.select(
            message="What do you want to do?",
            choices=list(choices.keys()) + [Choice(value=None, name="Stop Node")],
        ).execute()

        if result is None:
            is_done = inquirer.confirm(
                message="Are you sure you want to stop this node?", default=False
            ).execute()

        else:
            callback = choices[result]

            callback(tangle, node)

    Send.fail("Stopping Node...")

    node.stop()

    node.save_all_nodes()

    tangle.save()


@app.command()
def wallet():
    secret = inquirer.secret(
        message="Wallet Secret:",
        instruction="(blank to create new)",
    ).execute()

    if not secret:
        secret = None

    wallet = handle_pk_input(secret)

    if wallet is None:
        return

    Send.primary(f"ADDRESS: {wallet.address}\nPRIVATE KEY: {wallet.pk}")


@app.command()
def info():
    Send.primary(
        figlet_format("Thomas Coin")
        + '"The final currency"\n\nThomas coin is a lightweight DAG-based cryptocurrency designed for everyday applications.'
    )

    Send.secondary("\nGithub Repository: https://github.com/principle105/thomas-coin")


if __name__ == "__main__":
    app()
