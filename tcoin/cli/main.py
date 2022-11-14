from typing import Callable

import typer
import yaml
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from InquirerPy.utils import color_print
from InquirerPy.validator import EmptyInputValidator
from pyfiglet import figlet_format
from yaspin import yaspin
from yaspin.spinners import Spinners

from tcoin.constants import MIN_SEND_AMT
from tcoin.p2p.nodes import Node
from tcoin.tangle import Tangle
from tcoin.tangle.messages import Transaction, TransactionPayload
from tcoin.wallet import Wallet

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
    sent = 0

    for t in tangle.msgs.values():
        if isinstance(t, Transaction):
            sent += t.get_transaction().amt

    msg_total = len(tangle.all_msgs)
    unverified = len(tangle.all_tips)

    Send.primary(
        f"Total Messages: {msg_total}\n"
        f"Unverified Message: {unverified}\n"
        f"Total Sent: {sent}"
    )


def send(tangle: Tangle, node: Node):
    balance = tangle.get_balance(node.wallet.address)

    if balance < MIN_SEND_AMT:
        return Send.fail(
            f"You have less than the minimum send amount {MIN_SEND_AMT}"
        )

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

    # Constructing the transaction
    payload = TransactionPayload(receiver=address, amt=amount)

    index = tangle.get_transaction_index(node.wallet.address)

    index = inquirer.number(
        message="Index:", default=index, validate=EmptyInputValidator()
    ).execute()

    index = int(index)

    msg = node.create_message(
        Transaction, index=index, payload=payload.to_dict()
    )

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

    msg_data = msg.to_dict()

    is_sem_valid = node.handle_new_message(msg_data)

    # Checking if the message is valid
    if is_sem_valid is False:
        return Send.fail("Semantically invalid!")

    Send.success("Queued transaction")

    with Send.spinner("Broadcasting Transaction"):
        node.send_to_nodes(msg_data)

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


def view_branch(tangle: Tangle, _):
    node_id = inquirer.text(
        message="Node ID:",
        validate=EmptyInputValidator(),
    ).execute()

    index = inquirer.number(
        message="Index:", validate=EmptyInputValidator()
    ).execute()

    index = int(index)

    branch_id = (node_id, index)

    branch = tangle.branches.get(branch_id, None)

    if branch is None:
        return Send.fail("Branch not found")

    Send.primary(f"\n\nBranch ID: {branch_id}")

    for i, b in enumerate(branch.conflicts.values()):
        Send.secondary(f"Branch: {i} - {len(b.msgs)}")

        state = tangle.state.merge(b.state).merge(
            branch.main_branch.state, add=False
        )

        balance = state.get_balance(branch_id[0])

        Send.regular(f"Branch Balance: {balance}")

    Send.regular("\n\n")


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
        tangle = Tangle.from_save(wallet)
        sp.write("- Loaded tangle from save")

        node = Node(
            host="",
            port=port,
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

    menu_options = {
        "Network": {
            "Connect": connect,
            "Node Stats": node_stats,
        },
        "Tangle": {
            "Tangle Stats": tangle_stats,
            "View Message": view_msg,
            "Balance": view_balance,
            "View Branch": view_branch,
        },
        "Send": send,
        "View Address": view_address,
    }

    is_done = False
    prev_options = []
    options = menu_options

    while is_done is False:

        while True:
            choices = list(options.keys())

            if options == menu_options:
                choices.append(Choice(value=0, name="Stop Node"))

            else:
                choices.append(Choice(value=1, name="Back"))

            result = inquirer.select(
                message="What do you want to do?",
                choices=choices,
                border=True,
                instruction="Use the arrow keys",
            ).execute()

            if result == 0:
                is_done = inquirer.confirm(
                    message="Are you sure you want to stop this node?",
                    default=False,
                ).execute()
                break

            elif result == 1:
                options = prev_options

            else:
                callback = options[result]

                if isinstance(callback, Callable):
                    callback(tangle, node)
                    break

                prev_options = options
                options = callback

    Send.fail("Stopping Node...")

    node.save_all_nodes()

    node.stop()

    tangle.save(node.wallet)


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

    Send.primary(f"Address: {wallet.address}")

    if secret is None:
        Send.secondary(f"Private Key: {wallet.pk}")


@app.command()
def info():
    Send.primary(
        figlet_format("Thomas Coin")
        + '"The final currency"\n\nThomas coin is a lightweight DAG-based cryptocurrency designed for everyday applications.'
    )

    Send.secondary(
        "\nGithub Repository: https://github.com/principle105/thomas-coin"
    )


if __name__ == "__main__":
    app()
