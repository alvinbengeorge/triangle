from langgraph.graph import StateGraph, MessagesState, START, END
from generation import generate_text
from database import BasicChromaDB
from model import Client
from ollama import chat

import os

class Pipeline:
    def __init__(self, client):
        self.client = client
        self.COMPANY = {
            "name": "Alvin Company",
            "email": "alvincompany@gmail.com",
            "phone number": ["+91 9448800900", "+91 44 24299892"]
        }
        
        self.database = BasicChromaDB()
        self._load_knowledge_base()

        self.graph = StateGraph(MessagesState)

        self.graph.add_node(self.retrieval_action)
        self.graph.add_node(self.understanding_problem)
        self.graph.add_node(self.create_a_note_to_developer)
        self.graph.add_node(self.create_a_reply_to_client)
        self.graph.add_node(self.store_ticket)

        self.graph.add_edge(START, self.retrieval_action.__name__)
        self.graph.add_edge(self.retrieval_action.__name__, self.understanding_problem.__name__)
        self.graph.add_edge(self.understanding_problem.__name__, self.create_a_note_to_developer.__name__)
        self.graph.add_edge(self.create_a_note_to_developer.__name__, self.create_a_reply_to_client.__name__)
        self.graph.add_edge(self.create_a_reply_to_client.__name__, self.store_ticket.__name__)
        self.graph.add_edge(self.store_ticket.__name__, END)

        self.graph = self.graph.compile()

        self.developer_note = ""
        self.client_reply = ""
        self.user_input = ""
    
    def invoke(self, prompt: str) -> MessagesState:
        initial_state = {"messages": [{"role": "user", "content": prompt}]}
        self.user_input = prompt
        return self.graph.invoke(initial_state)
    
    def _load_knowledge_base(self, storage_folder="./storage"):
        self.database.reset_database()
        self.database.load_markdown_files(storage_folder)

    def _get_similar(self, query_text: str, n_results: int = 5):
        results = self.database.query(query_text, n_results)
        return results
    
    def retrieval_action(self, state: dict) -> MessagesState:
        print("[started] RETRIEVAL ACTION")
        user_query = state['messages'][-1].content
        results = self._get_similar(user_query, n_results=3)
        
        retrieved_info = "\n\n".join(
            [f"Document ID: {doc_id}\nContent: {doc_content}" 
             for doc_id, doc_content in zip(results['ids'][0], results['documents'][0])]
        )
        print(f"[INFO] Retrieved document IDs: {results['ids'][0]}")
        print(f"[INFO] Retrieved documents: {len(results['documents'][0])} documents found")
        
        response_content = f"Based on complain, here are some relevant documents:\n\n{retrieved_info}"        
        return {"messages": state['messages'] + [{"role": "assistant", "content": response_content}]}
    
    def understanding_problem(self, state: dict):
        print("[started] UNDERSTANDING THE PROBLEM")
        user_query = state['messages'][-2].content
        retrieved_info = state['messages'][-1].content
        prompt = f"""
You are an assistant that is responsible for understanding the problem given by the user and compare with the past problems, and create a summary of what the problem could be and if it has been resolved or not
Go through them and find out if similar problems occured before.
        
USER COMPLAINT: 
{user_query}

HISTORY:
{retrieved_info}

Summarize and give a brief. Take only relevant documents from the history information answer.
If a similar or same problem was found to be resolved, then it can be ignored
"""
        response = generate_text(prompt)
        return {"messages": state['messages'] + [{"role": "assistant", "content": response}]}
    
    def create_a_note_to_developer(self, state: dict):
        print("[started] NOTE TO DEVELOPER ACTION")
        user_query = state['messages'][-3].content
        retrieved_info = state['messages'][-2].content
        problem_summary = state['messages'][-1].content
        prompt = f"""
You are a bot that is responsible for taking all the given details given below about the problems the user is facing and give it off to a developer written in markdown for notion app
Please go through this carefully and find the relevant symptoms of the bug and create a markdown for developers

USER PROBLEM:\n{user_query}
RETRIEVED HISTORY:\n{retrieved_info}
PROBLEM SUMMARY:\n{problem_summary}

READ THROUGH THIS AND UNDERSTAND THE PROBLEM AND LIST OUT THE PROBLEMS IN MARKDOWN FOR THE DEVELOPER.
GIVE A SIMPLE MARKDOWN ASKING TO CHECK FOR POSSIBLE PROBLEMS
        """
        response = generate_text(prompt)
        self.developer_note = response
        return {"messages": state['messages'] + [{"role": "assistant", "content": response}]}
    
    def create_a_reply_to_client(self, state: dict):
        print("[started] REPLY TO CLIENT ACTION")
        user_query = state['messages'][-4].content
        retrieved_info = state['messages'][-3].content
        problem_summary = state['messages'][-2].content
        prompt = f"""
You are a bot that is responsible for writing the final reply back to the user who complained, use formal tone and describe politely about the current situation in hand based on the details given below
Asses the situation given and make an email that would be of satisfactory to the user describing the time it could take based on the problem complexity

USER COMPLAIN:\n{user_query}
PAST COMPLAINS:\n{retrieved_info}
PROBLEM SUMMARY:\n{problem_summary}
NOTE TO DEVELOPER:\n{self.developer_note}

REMEMBER TO NOT PROVIDE ANY SECRETS OR ANYTHING RELATED TO THE CODEBASE FROM THE DEVELOPER NOTE
ONLY PROVIDE ONE EMAIL, JUST CREATE ONE EMAIL AND NOT MORE THAN THAT.
DO NOT PROVIDE A SOLUTION:
- If it is resolved, tell the client to please update to resolve
- If it is not resolved, tell the client to not worry and our developers will take care of it

COMPANY DETAILS:
{str(self.COMPANY)}

DETAILS OF THE CLIENT WHO COMPLAINED:
{str(self.client)}

TRY NOT TO PUT PLACEHOLDERS. DO NOT PUT ANY NOTES, just create the reply email
"""
        response = generate_text(prompt)
        self.client_reply = response
        return {"messages": state['messages'] + [{"role": "assistant", "content": response}]}
    
    def get_results(self):
        return {
            "dev": self.developer_note,
            "reply": self.client_reply
        }
    
    def _write_to_storage(self, complain: str):
        """Write complaint to storage as a markdown file"""
        try:
            if complain:
                existing_files = [f for f in os.listdir("./storage/") if f.endswith(".md")]
                file_number = len(existing_files) + 1
                file_name = f"./storage/{file_number}.md"
                formatted_content = f"# Complaint #{file_number}\n\n##Content\n{complain}\n\n##Client Details\nName: {self.client.name}\nPhone: {self.client.phone}\n"
                
                with open(file_name, "w") as f:
                    f.write(formatted_content)
                print(f"[INFO] Complaint stored as {file_name}")
                return True
        except Exception as e:
            print(f"[ERROR] Failed to store complaint: {e}")
        return False

    def store_ticket(self, state: dict):
        """Store the complaint ticket"""
        print("[started] STORE TICKET ACTION")
        user_query = state['messages'][0].content
        
        try:
            result = self._write_to_storage(user_query)            
            if result:
                storage_message = "Complaint successfully stored to knowledge base."
            else:
                storage_message = "Failed to store complaint."
                
            return {"messages": state['messages'] + [{"role": "assistant", "content": storage_message}]}
            
        except Exception as e:
            print(f"[ERROR] Store ticket failed: {e}")
            return {"messages": state['messages'] + [{"role": "assistant", "content": f"Storage failed: {str(e)}"}]}

if __name__ == "__main__":
    client = Client(name="Alvin", phone_number="9448638474")
    pipeline = Pipeline(client)
    
    new_state: MessagesState = pipeline.invoke(input("Enter your query: "))
    print("-----")
    print("FINISHED PROCESSING\n\n")
    result = pipeline.get_results()
    print("DEVELOPER NOTE:")
    print(result['dev'])
    print("--------------\n\nREPLY TO THE CLIENT:")
    print(result['reply'])


