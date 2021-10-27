# from base64 import b64encode


# class Signed_Stake:
#     def __init__(self, address: str, stake: int):
#         self.address = address
#         self.stake = stake

#     def get_hash(self):
#         data = f"{self.address}{self.state}"

#     def sign(self, wallet: Wallet):
#         return b64encode(wallet.sk.sign(self.hash.encode())).decode()
