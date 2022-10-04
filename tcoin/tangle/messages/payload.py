class Payload:
    def to_dict(self) -> dict:
        ...

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)
