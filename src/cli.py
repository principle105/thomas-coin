from wallet import Wallet


def show_start_menu():
    print("Welcome to thomas token (THOM)")


def create_wallet():
    secret = input("Wallet secret: ")
    if not secret:
        secret = None

    wallet = Wallet(secret=secret)
    return wallet

def start_node(ip: str, port: int):
    pass


if __name__ == "__main__":
    show_start_menu()

    wallet = create_wallet()
    print("ADDRESS:", wallet.address)
    print("PUBLIC KEY:", wallet.public_key)
    print("PRIVATE KEY:", wallet.private_key)
