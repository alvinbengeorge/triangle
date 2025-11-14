import chromadb
import os
import glob
from pathlib import Path

class BasicChromaDB:
    def __init__(self, collection_name="default_collection", persist_directory="./chroma_db"):
        """Initialize ChromaDB client and collection"""
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection_name = collection_name
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def reset_database(self):
        """Reset the database by deleting all documents in the collection"""
        count = self.get_collection_count()
        if count > 0:
            all_ids = [str(i) for i in range(count)]
            self.delete_documents(all_ids)
            print(f"Reset database: Deleted {count} documents")
        else:
            print("Database is already empty")
    
    def load_markdown_files(self, storage_folder="./storage"):
        """Load all markdown files from storage folder"""
        markdown_files = glob.glob(os.path.join(storage_folder, "*.md"))
        documents = []
        metadatas = []
        ids = []
        
        for file_path in markdown_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    documents.append(content)
                    
                    # Create metadata with file info
                    file_name = os.path.basename(file_path)
                    metadatas.append({
                        "filename": file_name,
                        "filepath": file_path
                    })
                    
                    # Use filename as ID (without extension)
                    file_id = Path(file_path).stem
                    ids.append(file_id)
                    
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
        
        if documents:
            self.add_documents(documents, metadatas, ids)
            print(f"Loaded {len(documents)} markdown files")
        else:
            print("No markdown files found in storage folder")
    
    def add_documents(self, documents, metadatas=None, ids=None):
        """Add documents to the collection"""
        if ids is None:
            ids = [f"doc_{i}" for i in range(len(documents))]
        
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
    
    def query(self, query_text, n_results=5):
        """Query the collection"""
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        return results
    
    def delete_documents(self, ids):
        """Delete documents by IDs"""
        self.collection.delete(ids=ids)
    
    def get_collection_count(self):
        """Get number of documents in collection"""
        return self.collection.count()

# Example usage
if __name__ == "__main__":
    db = BasicChromaDB()
    
    # Load markdown files from storage folder
    db.load_markdown_files("./storage")
    
    # Query the database
    results = db.query("app crashes", n_results=5)
    print(results) 