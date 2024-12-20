# -*- encoding: utf-8 -*-
"""
Initialize the aifypilot module, set up dependencies like vector_store,
text_splitter, wiki_wiki, and llm before they are used in routes.py.
"""

import openai
from langchain.chains import RetrievalQA
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.llms import OpenAI
import wikipediaapi

# Setup OpenAI API key if not already set
openai.api_key = openai.api_key or ""

# Initialize tools
llm = OpenAI(temperature=0.7)
embeddings = OpenAIEmbeddings()

# Create or load a vector store collection for documents
vector_store = Chroma(collection_name="finance_knowledge", embedding_function=embeddings)

# Initialize Wikipedia API
wiki_wiki = wikipediaapi.Wikipedia(
    language='en', 
    user_agent='Markets Analytics Hub/1.0 (https://marketanalyticshub.app/contact) Python/3.12'
)

# Text splitter for processing documents
text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
