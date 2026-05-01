from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

#Carregar arquivos
loader = DirectoryLoader(".", glob="**/*.py", loader_cls=TextLoader)
docs = loader.load()

#Dividir
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = splitter.split_documents(docs)

#Criar embeddings
embeddings = OpenAIEmbeddings()

#Criar banco vetorial
db = FAISS.from_documents(chunks, embeddings)

#Modelo
llm = ChatOpenAI(model="gpt-4o-mini")

#Pergunta
query = "O que esse projeto faz?"

docs_encontrados = db.similarity_search(query)

res = llm.invoke(f"""
Baseado nesses trechos de código:

{docs_encontrados}

Responda: {query}
""")

print(res.content)
