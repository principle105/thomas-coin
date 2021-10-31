from constants import MAX_AFFECTING_STAKE

# Idea from: https://medium.com/kleros/an-efficient-data-structure-for-blockchain-sortition-15d202af3247
# Kleros - Clément Lesaege
class Leaf:
    def __init__(self, left=None, right=None, adr=None, value=0):
        # Children
        self.left = left
        self.right = right

        # Address
        self.adr = adr

        # Stake / sum of of children
        if self.left and self.right:
            self.value = self.left.value + self.right.value
        else:
            self.value = value

    def search(self, num):
        prev = self.value

        # Checking if node has any children
        if self.left and self.right:

            s, l = self.left, self.right

            if self.left.value > self.right.value:
                s, l = l, s

            if prev and num > self.value:
                num -= prev

            prev = self.value

            if num <= s.value:
                return s.search(num)
            return l.search(num)

        return self.adr

    @classmethod
    def grow_branches(cls, data: list["Leaf"]):
        b = []
        # Groups leaves
        for i in range(0, len(data), 2):
            if i + 1 < len(data):
                b.append(cls(left=data[i], right=data[i + 1], adr=data[i].adr))

            else:
                b.append(cls(value=data[i].value, adr=data[i].adr))

        # Continues grouping if possible
        if len(b) > 1:
            return cls.grow_branches(b)

        return b[0]

    @classmethod
    def plant_tree(cls, data: dict):
        leaves = [
            cls(value=min(v["stake"], MAX_AFFECTING_STAKE), adr=a)
            for a, v in sorted(data.items(), key=lambda i: i[1]["stake"], reverse=True)
        ]

        return cls.grow_branches(leaves)
