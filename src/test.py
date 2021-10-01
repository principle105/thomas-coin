try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from blockchain import Block, Transaction

if __name__ == "__main__":
    t = Transaction(
        sender_key="GENESIS",
        receiver="Te32761fe9b7b617f327c5b428bd29d8b5b4d7929",
        amount=10000.0,
        tip=0.0,
        nonce=0,
        sender="GENESIS",
    )
    t.signature = "0"

    b = Block(index=0, prev="0", forger="0", transactions=[t])
    b.signature = "0"

    print(b.get_json())
