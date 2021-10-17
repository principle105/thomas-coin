try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from blockchain import Block, Transaction

if __name__ == "__main__":
    t = Transaction(
        sender="GENESIS",
        receiver="T26nNx7Ai2Je4EnXGKGPnXcEHqNntMhewnZFpJYhXjozWF",
        amount=10000.0,
        tip=0.0,
        nonce=0,
    )
    t.signature = "0"

    b = Block(index=0, prev="0", forger="0", difficulty=0, transactions=[t])
    b.signature = "0"

    print(b.get_json())
