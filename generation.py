import ollama

def generate_text(prompt: str, model: str = "llama3.2:1b") -> str:
    response = ollama.generate(model=model, prompt=prompt)
    return response['response']

