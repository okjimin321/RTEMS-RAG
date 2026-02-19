## RAG for RTEMS

### Summary

General LLMs such as GPT or Gemini do not have deep knowledge of specialized domains like RTEMS, which can lead to hallucinations.

This repository aims to eliminate incorrect information about RTEMS and provide reliable assistance for RTEMS development and environment setup.

---

### Technical Explanation

**Initial Step**

PDF documentation is converted to Markdown using Llama Cloud.

This improves parsing quality and overall retrieval performance.

**Embedding**

Documents are loaded and embedded using FastEmbed.

(Heavier embedding models can be used to improve accuracy.)

Embeddings are stored in a vector store to enable reuse without recomputation.

**Search**

This system uses a hybrid retrieval approach:

- **Vector search** — retrieves contextually similar content
- **BM25 search** — retrieves keyword-based matches

Initially, only vector search was used. However, RTEMS documentation contains many technical terms, making keyword matching essential.

Therefore, a hybrid retriever is used.

**Generation**

Ollama is used as the LLM backend.

The prompt configures the model to act as an RTEMS expert.

Search results from the hybrid retriever are passed to the LLM to generate answers.

**Grounding & Verification**

To evaluate retrieval success, answers include source references from the documentation.

---

### Usage

**Recommended environment:** Python 3.12

1. If you want to add additional documentation, convert PDF files to Markdown and place them in the `/docs` directory.
2. Download the LLM model and Python packages:
    
    ```bash
    ollama pull llama3.2
    pip install -r requirements.txt
    ```
    
    *(You may use a different model if desired.)*
    
3. Start Ollama in the background:
    
    ```bash
    ollama serve
    ```
    
4. Run the script:
    
    ```bash
    python3 main.py
    ```
    
5. Enter your query:
    
    ```
    [QUERY]: How does the RTEMS scheduler handle priority inheritance?
    ```