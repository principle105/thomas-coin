try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from blockchain import Block, Transaction

if __name__ == "__main__":
    t = Transaction(
        sender_key="GENESIS",
        receiver="T6a0459220225c6b4bfaef26ec87844a072afc29a",
        amount=10000.0,
        tip=0.0,
        nonce=0,
        sender="GENESIS",
    )
    t.signature = "0"

    b = Block(index=0, prev="0", forger="0", transactions=[t])
    b.signature = "0"

    print(b.get_json())
