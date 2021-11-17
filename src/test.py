from blockchain import Block, Transaction

# Creating the genesis block
if __name__ == "__main__":
    t = Transaction(
        sender="GENESIS",
        receiver="T26nNx7Ai2Je4EnXGKGPnXcEHqNntMhewnZFpJYhXjozWF",
        amount=10000.0,
        tip=0.0,
        nonce=0,
    )
    t.signature = "0"

    b = Block(index=0, prev="0", forger="GENESIS", difficulty=4, transactions=[t])
    b.signature = "0"

    print(b.get_json())
