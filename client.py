class Client:
    def __init__(self, name: str, phone_number: str):
        self.name = name
        self.phone = phone_number

    def __dict__(self):
        return {
            "name": self.name,
            "phone": self.phone
        }
    
    def __str__(self):
        return f"""
NAME: {self.name}
PHONE: {self.phone}
"""