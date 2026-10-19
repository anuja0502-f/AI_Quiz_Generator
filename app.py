
import os
import json
import random
import streamlit as st
from pypdf import PdfReader
from openai import OpenAI

st.set_page_config(
    page_title="AI Quiz Generator",
    page_icon="🧠",
    layout="centered"
)

st.title("🧠 AI-Powered Educational Quiz Generator")
st.write("Generate MCQs, test your knowledge, and view your results.")

# Built-in questions for testing without an API key
DEMO_QUESTIONS = [
    {
        "question": "What does AI stand for?",
        "options": [
            "Automated Internet", "Artificial Intelligence",
            "Advanced Interface", "Applied Information"
        ],
        "answer": "Artificial Intelligence",
        "explanation": "AI stands for Artificial Intelligence, which enables machines to perform tasks that normally require human intelligence."
    },
    {
        "question": "Which is an example of machine learning?",
        "options": [
            "A basic light switch",
            "A system learning patterns from data",
            "A printed textbook",
            "A standard ruler"
        ],
        "answer": "A system learning patterns from data",
        "explanation": "Machine learning uses data to identify patterns and make predictions or decisions."
    },
    {
        "question": "What is the main purpose of training data?",
        "options": [
            "To decorate a computer",
            "To increase screen brightness",
            "To help a model learn patterns",
            "To replace the operating system"
        ],
        "answer": "To help a model learn patterns",
        "explanation": "Training data provides examples from which a machine learning model learns."
    },
    {
        "question": "Which of these is a programming language?",
        "options": ["Python", "HTML page title", "Wi-Fi", "Keyboard"],
        "answer": "Python",
        "explanation": "Python is a general-purpose programming language widely used in AI and data science."
    },
    {
        "question": "What is one responsible way to use AI?",
        "options": [
            "Trust every output without checking",
            "Share private data publicly",
            "Verify important information",
            "Ignore all errors"
        ],
        "answer": "Verify important information",
        "explanation": "AI output can contain errors, so important information should be checked against reliable sources."
    }
]


def extract_text(uploaded_file):
    """Read text from an uploaded TXT or PDF file."""
    if uploaded_file is None:
        return ""

    if uploaded_file.name.lower().endswith(".txt"):
        return uploaded_file.getvalue().decode(
            "utf-8", errors="ignore"
        )

    if uploaded_file.name.lower().endswith(".pdf"):
        reader = PdfReader(uploaded_file)
        return "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        )

    return ""


def generate_questions(topic, material, count):
    """Generate MCQs using an AI model, if configured."""
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return random.sample(
            DEMO_QUESTIONS,
            min(count, len(DEMO_QUESTIONS))
        ), True

    client = OpenAI(api_key=api_key)

    source = material.strip() or topic.strip()
    source = source[:15000]

    prompt = f"""
Create exactly {count} educational multiple-choice questions
using the following topic or study material.

SOURCE:
{source}

Return ONLY valid JSON in this format:
{{
  "questions": [
    {{
      "question": "Question text",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "answer": "Exact text of the correct option",
      "explanation": "Brief explanation"
    }}
  ]
}}

Requirements:
- Exactly four distinct options per question.
- Exactly one correct answer per question.
- The answer must exactly match one option.
- Explanations should be clear and educational.
- Questions should be relevant to the source.
- Do not add markdown or text outside the JSON.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You create accurate educational quizzes."
            },
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.5
    )

    data = json.loads(
        response.choices[0].message.content
    )
    questions = data["questions"]

    if len(questions) != count:
        raise ValueError("The AI returned an unexpected number of questions.")

    for q in questions:
        if (
            len(q.get("options", [])) != 4
            or q.get("answer") not in q.get("options", [])
            or len(set(q.get("options", []))) != 4
        ):
            raise ValueError("An AI-generated question is invalid.")

    return questions, False


# Input section
topic = st.text_input(
    "Enter a topic",
    placeholder="e.g. Artificial Intelligence"
)

uploaded_file = st.file_uploader(
    "Or upload study material",
    type=["txt", "pdf"]
)

num_questions = st.slider(
    "Number of questions",
    min_value=5,
    max_value=10,
    value=5
)

if st.button("Generate Quiz", type="primary"):
    if not topic.strip() and uploaded_file is None:
        st.warning("Please enter a topic or upload study material.")
    else:
        try:
            material = extract_text(uploaded_file)

            if uploaded_file is not None and not material.strip():
                st.error(
                    "No readable text was found. "
                    "Please use a text-based PDF or TXT file."
                )
                st.stop()

            with st.spinner("Preparing your quiz..."):
                questions, demo_mode = generate_questions(
                    topic, material, num_questions
                )

            st.session_state.questions = questions
            st.session_state.demo_mode = demo_mode
            st.session_state.submitted = False
            st.session_state.answers = {}

        except Exception as e:
            st.error(f"Could not generate the quiz: {e}")

# Quiz section
if st.session_state.get("questions"):
    questions = st.session_state.questions

    if st.session_state.get("demo_mode"):
        st.info(
            "Demo mode: sample AI-related questions are shown. "
            "Configure OPENAI_API_KEY for topic-specific AI generation."
        )

    st.subheader("📝 Take Your Quiz")

    if not st.session_state.get("submitted", False):
        with st.form("quiz_form"):
            selected_answers = {}

            for i, q in enumerate(questions):
                st.markdown(f"**Q{i + 1}. {q['question']}**")

                selected_answers[str(i)] = st.radio(
                    "Choose an answer:",
                    q["options"],
                    index=None,
                    key=f"answer_{i}"
                )
                st.divider()

            submitted = st.form_submit_button(
                "Submit Quiz",
                type="primary"
            )

        if submitted:
            st.session_state.answers = selected_answers
            st.session_state.submitted = True
            st.rerun()

    # Results section
    if st.session_state.get("submitted", False):
        answers = st.session_state.answers
        score = sum(
            answers.get(str(i)) == q["answer"]
            for i, q in enumerate(questions)
        )
        total = len(questions)
        percentage = score / total * 100

        st.subheader("🏆 Your Results")
        st.metric("Final Score", f"{score} / {total}")
        st.progress(percentage / 100)
        st.write(f"**Percentage:** {percentage:.1f}%")

        if percentage == 100:
            st.success("Excellent! Perfect score!")
        elif percentage >= 80:
            st.success("Great work! You have a strong understanding.")
        elif percentage >= 60:
            st.info("Good effort! Review the incorrect answers.")
        else:
            st.warning("Keep practising and revisit the study material.")

        st.subheader("Answer Review")

        for i, q in enumerate(questions):
            chosen = answers.get(str(i))
            correct = chosen == q["answer"]

            st.markdown(f"**Q{i + 1}. {q['question']}**")

            if correct:
                st.success(f"Your answer: {chosen}")
            else:
                st.error(f"Your answer: {chosen or 'Not answered'}")
                st.write(f"Correct answer: {q['answer']}")

            st.write(f"Explanation: {q['explanation']}")
            st.divider()

        if st.button("Create Another Quiz"):
            st.session_state.questions = []
            st.session_state.answers = {}
            st.session_state.submitted = False
            st.rerun()
