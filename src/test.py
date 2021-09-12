from transaction import Transaction
from wallet import Wallet

sender = Wallet()
receiver = Wallet()

t = Transaction(sender.public_key, receiver.address, 100, 0)
signature = t.sign(sender.private_key)
t.signature = signature

print(t.is_signature_valid())
