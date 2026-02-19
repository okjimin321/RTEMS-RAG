from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders import DirectoryLoader
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS # 대규모 벡터 연산을 위한 라이브러리
import os
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain_ollama import ChatOllama

# docs 디렉토리에서 load
loader = DirectoryLoader("docs/", glob="*.md", loader_cls=TextLoader)
documents = loader.load() # document 객체 배열 

# split 규칙 설정
headers_to_split_on = [
    ("#", "chapter"),
    ("##", "section"),
    ("###", "subsection"),
    ("####", "subsubsection"),
]

# header 기준으로 1차 분할
markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
header_splitted_docs = []

for doc in documents:
    
    partial_docs = markdown_splitter.split_text(doc.page_content)
    # 어떤 파일인지 정보 추가
    for p_doc in partial_docs:
        p_doc.metadata["source"] = doc.metadata["source"]

    header_splitted_docs.extend(partial_docs)

# 문자 단위로 2차 분할 (메타 데이터(구조)는 동일한 상태에서 내용만 더 잘게 자름.)
chunk_size = 800
chunk_overlap = 300

text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
final_splitted_docs = text_splitter.split_documents(header_splitted_docs)

# 임베딩 단계 (로컬에 있는 모델)
# cpu
embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")

vectorstore = None
if os.path.exists("vectors_store"):
    vectorstore = FAISS.load_local("vectors_store", embeddings, allow_dangerous_deserialization=True)
else:    
    vectorstore = FAISS.from_documents(
        final_splitted_docs,
        embedding=embeddings
    )
    vectorstore.save_local("vectors_store")

# 검색 설정 단계
vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 3, "fetch_k" : 20}) # 의미 유사도 기반 검색
bm25_retriever = BM25Retriever.from_documents(final_splitted_docs) # 키워드 기반 검색
hybrid_retriever = EnsembleRetriever(
    retrievers=[vector_retriever, bm25_retriever],
    weights=[0.5, 0.5]
)

model = ChatOllama(
    model="llama3.2:latest",
    base_url="http://localhost:11434",
    temperature=0.2,
)

prompt = ChatPromptTemplate.from_template("""
[SYSTEM_ROLE]
You are a Senior RTEMS Kernel Engineer specializing in real-time operating systems and BSP development. Your goal is to provide a highly technical and accurate explanation based ONLY on the provided <context>.

[COGNITIVE_STEPS]
1. Identify the core RTEMS component related to the question (e.g., Score, POSIX API, BSP, Build System).
2. Scan the context for specific C structures, macro definitions, or configuration variables.
3. If the context describes a function's behavior in text (e.g., "returns X"), treat it as a factual implementation detail even if the direct C code snippet is missing.
4. Synthesize the final answer by connecting low-level implementation details with high-level OS concepts.

[CONSTRAINTS]
- If the answer is not in the context, state: "The requested information is not available within the provided documentation."
- Do not hallucinate function names, file paths, or configuration keys.
- Keep explanations concise but technically dense (C-level depth).
- The entire response must be written in English.

[OUTPUT_FORMAT]
- Technical Explanation: (Provide a clear summary of the RTEMS kernel logic or core concept)
- Implementation & Symbols: (List function names, specific return values, constants, or file paths found in the context)
- Rationale: (Briefly state which part of the context supports this answer to ensure grounding)
- Documentation Ref: (Specific Chapter or Section names from metadata)

<context>
{context}
</context>

Question: {input}

Answer:
""")

combine_docs_chain = create_stuff_documents_chain(model, prompt)
chain = create_retrieval_chain(hybrid_retriever, combine_docs_chain)

query = input(f"\n\n\033[1;34m[QUERY]:\033[0m ")
while query != "bye":
    
    result = chain.invoke({"input" : query})

    # --- [출력 부분] ---
    print(f"\n\033[1;32m[SYSTEM] Query processing complete.\033[0m")
    print(f"\033[1;33m[AGENT]\033[0m")
    print(result['answer'])
    
    retrievel_result = hybrid_retriever.invoke(query) # source 출력용  
    print(f"\n\033[1;35m[SOURCE]\033[0m")
    for  doc in retrievel_result:
        
        meta = doc.metadata
    
        source = meta.get("source", "N/A") # 어떤 파일에서 왔는지 
        chapter = meta.get("chapter", "N/A")
        section = meta.get("section", "N/A")
        subsection = meta.get("subsection", "N/A")
        location = f"{source} ❯ {chapter} ❯ {section} ❯ {subsection}"
    
        print(f"\033[1;36m{location}\033[0m")
    
        # 구분선 (Sub-subsection이 있다면 추가 출력)
        if 'subsubsection' in meta:
            print(f"\033[0;90m└─ Sub-sub: {meta['subsubsection']}\033[0m")
    
        #print("\033[1;30m" + "━" * 80 + "\033[0m") # 어두운 회색 구분선
    
        #  본문 내용 (strip으로 불필요한 공백 제거)
        #content = doc.page_content.strip()
        #print(content)
    
        #print("\033[1;30m" + "━" * 80 + "\033[0m")
    # 다음 질문
    query = input(f"\n\033[1;34m[QUERY]:\033[0m ")

