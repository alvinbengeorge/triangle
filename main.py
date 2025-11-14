from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pipeline import Pipeline
from model import Ticket, Client

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/process_query/")
async def process_query(ticket: Ticket):
    client = Client(name=ticket.name, phone_number=ticket.phone)
    pipeline = Pipeline(client)
    pipeline.invoke(ticket.complaint)    
    return pipeline.get_results()

