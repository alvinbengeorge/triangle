from pydantic import BaseModel

class Client(BaseModel):
    name: str
    phone: str

class Ticket(BaseModel):
    name: str
    phone: str
    complaint: str