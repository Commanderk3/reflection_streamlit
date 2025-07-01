# Reflection Learning

A reflective learning chatbot built using Streamlit and powered by LLMs. It asks thoughtful questions, summarizes conversations, and provides insights to support metacognitive development.


## 🧠 Features

- 🤖 Reflective question generation
- 📝 Real-time summary of conversations
- 📊 Planned: Learning analysis from past sessions
- 🌐 LLM-powered with Streamlit frontend

## 🛠️ Tech Stack

- **Frontend:** Streamlit
- **Backend:** Python, LangChain, Gemini API
- **Vector Database:** Qdrant Cloud
- **LLMs:** Google Gemini 2.5 Flash, Google Gemini 1.5 Flash
- **Sentence Transformer:** `all-MiniLM-L6-v2`

## 📦 Installation

Clone the repository:

```bash
git clone https://github.com/Commanderk3/reflection_streamlit.git
cd reflection_streamlit
````

Install dependencies:

```bash
pip install -r requirements.txt
```

(Optional but recommended) Set up a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

## ▶️ Run the App

```bash
streamlit run app.py
```

## ⚙️ Environment Variables

Create a `.env` file in the root directory and add your keys:

```env
GOOGLE_API_KEY=your_google_api_key
```

## 🧪 Development Notes

* This project uses Gemini 2.5 Flash with `think` mode enabled by default.
* LLM reasoning capabilities are configurable.
* Planning to integrate analysis from previous summaries soon.

## 📄 License

This project follows [GNU AGPL v3.0](https://www.gnu.org/licenses/agpl-3.0.en.html).

## 📞 Contact

Made by [@Commanderk3](https://github.com/Commanderk3)
Email: [diwangshukakoty@gmail.com](diwangshukakoty@gmail.com)





