from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_classic.memory import VectorStoreRetrieverMemory
from langchain_classic.chains import ConversationChain
from langchain_google_genai import ChatGoogleGenerativeAI

import os
from dotenv import load_dotenv

load_dotenv()

CHROMA_DB_DIR = "chroma_storage"  # Persisted DB folder

user_chains = {}

def get_meal_coach_chain(user_id: str):
    if user_id in user_chains:
        return user_chains[user_id]

    # Use Gemini Embeddings
    embedding_model = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

    # Create/load user-specific Chroma DB
    vectorstore = Chroma(
        collection_name=f"user_memory_{user_id}",
        embedding_function=embedding_model,
        persist_directory=CHROMA_DB_DIR
    )

    memory = VectorStoreRetrieverMemory(retriever=vectorstore.as_retriever())

    llm = ChatGoogleGenerativeAI(
        model="gemini-3.6-flash",
        temperature=0.4,
    )

    chain = ConversationChain(
        llm=llm,
        memory=memory,
        verbose=True
    )

    user_chains[user_id] = chain
    return chain