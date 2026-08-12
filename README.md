#  URL Q&A: Full-Stack RAG Application

*Full-stack LLM application with OpenAI, Flask, React, and Pinecone*

<img src="https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExczdhcjIyZTd1YWZmdDdsem1rbTd3c2VjYnR6YmtmcTF5bjFuajAzciZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/oolHrmHDE9XtZtSLG8/giphy.gif" width="800">

This is a sample application built for the following tutorial series, "Build a full-stack LLM application with OpenAI, Flask, React, and Pinecone". It allows a user to input a URL and ask questions about the content of that webpage. It demonstrates the use of Retrieval Augmented Generation, OpenAI, and vector databases.

* **[Part 1](https://shwinda.medium.com/build-a-full-stack-llm-application-with-openai-flask-react-and-pinecone-part-1-f3844429a5ef):** Backend and RAG with Python, OpenAI, and Pinecone ([branch](https://github.com/ashnkumar/llm-full-stack-tutorial/tree/part1_backend))
* **[Part 2](https://shwinda.medium.com/build-a-full-stack-llm-application-with-openai-flask-react-and-pinecone-part-2-ceda4e290c33):** Front-end chat user interface with React ([branch](https://github.com/ashnkumar/llm-full-stack-tutorial/tree/part2_frontend))

> ** Note on SDK Deprecations:** Written in November 2023, the SDKs have moved since. The code on `main` is pinned to older legacy OpenAI and Pinecone clients. Methods like `pinecone.init()` have been completely removed from current versions. For modern deployments, refer to the active community migration updates.

---

##  Architecture Workflow

The complete end-to-end data pipeline is structured across two distinct primary execution runtime loops:

### [1] Ingestion and Embedding Pipeline
1. **React Web Application:** Accepts a user-inputted URL string and dispatches it over HTTP to the backend.
2. **Flask Backend Engine:** Automatically triggers a programmatic scraping routine to isolate text raw data from the DOM target.
3. **OpenAI Embedding API:** Translates the extracted web page text strings into uniform, high-dimensional floating-point vector arrays.
4. **Pinecone Vector Database:** Uploads, registers, and indexes the compiled vector profiles into long-term cloud memory storage.

### [2] Semantic Query and Answer Processing Loop
1. **React Chat Interface:** Dispatches the user's plain-text prompt/question directly downstream to the backend handler.
2. **Flask Orchestration Core:** Relays the user question to the OpenAI Embedding API to synthesize a matching query vector representation.
3. **Pinecone Similarity Matching:** Executes a vector neighborhood search to retrieve the top similar, relevant context slices from the index database.
4. **Prompt Context Formulation:** Dynamically builds a consolidated instruction prompt embedding the verified web text pieces as strict structural context boundaries.
5. **OpenAI Chat Completion API:** Passes the final payload stack over to GPT-4 to generate a reliable synthetic answer and streams it back to the client.

---

##  Local Environment Setup

**Install Python dependencies**
```sh
pip install -r requirements.txt
```

**Install React dependencies**
```sh
cd client
npm install
```

**Create .env configuration file**
```sh
OPENAI_API_KEY=<YOUR_API_KEY>
PINECONE_API_KEY=<YOUR_API_KEY>
```

**Start the Flask backend server**
```sh
# Run from the root workspace folder directory
python run.py
```

**Start the React frontend application**
```sh
cd client
npm start
```

---

## 📜 License
Distributed under the open-source MIT License — see [LICENSE](LICENSE) for full usage and redistribution rules.
