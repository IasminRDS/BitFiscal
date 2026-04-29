from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 1. Carregar arquivos
loader = DirectoryLoader(".", glob="**/*.py", loader_cls=TextLoader)
docs = loader.load()

# 2. Dividir
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = splitter.split_documents(docs)

# 3. Criar embeddings
embeddings = OpenAIEmbeddings()

# 4. Criar banco vetorial
db = FAISS.from_documents(chunks, embeddings)

# 5. Modelo
llm = ChatOpenAI(model="gpt-4o-mini")

# 6. Pergunta
query = "O que esse projeto faz?"

docs_encontrados = db.similarity_search(query)

res = llm.invoke(f"""
Baseado nesses trechos de código:

{docs_encontrados}

Responda: {query}
""")

print(res.content)
