import json
import re
import os
from pathlib import Path

import streamlit as st
from google import genai
from google.genai import types

MODEL_ID = os.environ.get("MODEL_ID", "gemini-2.5-flash")
PROGRESS_DIR = Path("progress")
PROGRESS_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Subject / topic catalog
# Add more subjects or topics here -- everything downstream is data-driven,
# the agent generates notes and questions for whatever you list.
# ---------------------------------------------------------------------------

SUBJECTS = {
    "python": {
        "name": "Python programming",
        "icon": "\U0001F40D",
        "topics": {
            "basics": {"name": "Python basics", "subskills": ["Variables & data types", "Operators & expressions", "Input/output", "Control flow (if/loops)"]},
            "functions": {"name": "Functions & modules", "subskills": ["Defining functions", "Arguments & return values", "Scope", "Modules & imports"]},
            "oop": {"name": "Object-oriented Python", "subskills": ["Classes & objects", "Inheritance", "Polymorphism & encapsulation", "Magic methods"]},
            "data_structures": {"name": "Data structures", "subskills": ["Lists & tuples", "Dictionaries & sets", "List comprehensions", "Iterators & generators"]},
            "exceptions_files": {"name": "Exceptions & file handling", "subskills": ["Try/except", "Custom exceptions", "Reading/writing files", "Context managers"]},
        },
    },
    "java": {
        "name": "Java programming",
        "icon": "\u2615",
        "topics": {
            "basics": {"name": "Java basics", "subskills": ["Variables & data types", "Operators", "Control flow", "Arrays"]},
            "oop": {"name": "OOP in Java", "subskills": ["Classes & objects", "Inheritance", "Polymorphism", "Abstraction & interfaces"]},
            "exceptions": {"name": "Exception handling", "subskills": ["Try/catch/finally", "Checked vs unchecked", "Custom exceptions", "Throw vs throws"]},
            "collections": {"name": "Collections framework", "subskills": ["List / ArrayList", "Set / HashSet", "Map / HashMap", "Iterators"]},
            "multithreading": {"name": "Multithreading basics", "subskills": ["Thread creation", "Runnable interface", "Synchronization", "Thread lifecycle"]},
        },
    },
    "dbms": {
        "name": "DBMS",
        "icon": "\U0001F5C4\uFE0F",
        "topics": {
            "er_normalization": {"name": "ER model & normalization", "subskills": ["ER diagrams", "Functional dependencies", "Normal forms (1NF-3NF)", "BCNF"]},
            "sql": {"name": "SQL queries", "subskills": ["SELECT & filtering", "Joins", "Aggregate functions & GROUP BY", "Subqueries"]},
            "transactions": {"name": "Transactions & concurrency", "subskills": ["ACID properties", "Concurrency control", "Locking", "Deadlocks"]},
            "keys_constraints": {"name": "Keys, constraints & indexing", "subskills": ["Primary & foreign keys", "Candidate keys", "Constraints", "Indexes"]},
        },
    },
    "dsa": {
        "name": "Data structures & algorithms",
        "icon": "\U0001F333",
        "topics": {
            "arrays_strings": {"name": "Arrays & strings", "subskills": ["Array operations", "String manipulation", "Two-pointer technique", "Sliding window"]},
            "linked_lists": {"name": "Linked lists", "subskills": ["Singly linked lists", "Doubly linked lists", "Reversal", "Cycle detection"]},
            "trees_graphs": {"name": "Trees & graphs", "subskills": ["Binary trees", "Binary search trees", "Tree traversals", "Graph BFS/DFS"]},
            "sorting_searching": {"name": "Sorting & searching", "subskills": ["Bubble/insertion/selection sort", "Merge sort & quicksort", "Binary search", "Time complexity analysis"]},
        },
    },
    "os": {
        "name": "Operating systems",
        "icon": "\U0001F5A5\uFE0F",
        "topics": {
            "process_management": {"name": "Process management", "subskills": ["Process states", "Process control block", "Context switching", "Inter-process communication"]},
            "scheduling": {"name": "CPU scheduling", "subskills": ["FCFS & SJF", "Round robin", "Priority scheduling", "Scheduling metrics"]},
            "memory_management": {"name": "Memory management", "subskills": ["Paging", "Segmentation", "Virtual memory", "Page replacement algorithms"]},
            "deadlocks_synchronization": {"name": "Deadlocks & synchronization", "subskills": ["Deadlock conditions", "Deadlock prevention/avoidance", "Semaphores & mutexes", "Producer-consumer problem"]},
        },
    },
}

SYSTEM_JSON_ONLY = (
    "You are an expert computer science tutor agent for engineering (B.Tech) students. "
    "Output ONLY valid JSON, no preamble, no markdown fences, no commentary."
)


# ---------------------------------------------------------------------------
# Agent core
# ---------------------------------------------------------------------------

@st.cache_resource
def get_client():
    api_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY"))
    if not api_key:
        st.error("No GEMINI_API_KEY found. Add it to .streamlit/secrets.toml (local) "
                  "or your app's Secrets settings (deployed). Get a free key at "
                  "https://aistudio.google.com/apikey")
        st.stop()
    return genai.Client(api_key=api_key)


def call_agent(system: str, user: str, max_tokens: int = 1000) -> dict:
    client = get_client()
    response = client.models.generate_content(
        model=MODEL_ID,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            max_output_tokens=max_tokens,
        ),
    )
    text = response.text or ""
    cleaned = re.sub(r"```json|```", "", text).strip()
    return json.loads(cleaned)


def agent_generate_notes(subject_name, topic_name, subskills):
    user = (
        f'Write concise study notes for a B.Tech student on the topic "{topic_name}" '
        f'in "{subject_name}", covering these subskills: {", ".join(subskills)}. '
        f'Keep explanations clear and exam-relevant. Include one short code example if the '
        f'subject is a programming language, or a short illustrative example otherwise. '
        f'Return JSON exactly: {{"overview": "2-3 sentence summary of the topic", '
        f'"keyConcepts": [{{"title": "string", "explanation": "2-4 sentences"}}, ...one per '
        f'subskill], "example": {{"language": "python|java|sql|text", "code": "string (empty '
        f'string if not applicable)", "explanation": "1-2 sentences on what the example shows"}}, '
        f'"commonMistakes": ["string", "string", "string"]}}'
    )
    return call_agent(SYSTEM_JSON_ONLY, user, max_tokens=1800)


def agent_diagnose(subject_name, topic):
    user = (
        f'Create one multiple-choice diagnostic question for EACH of these subskills in '
        f'"{topic["name"]}" ({subject_name}): {", ".join(topic["subskills"])}. Each question '
        f'should be quick to answer and reveal whether the student understands that specific '
        f'subskill. If code is relevant, keep snippets short. Return JSON exactly: '
        f'{{"reasoning": "one sentence on your diagnostic strategy", "questions": [{{"id": '
        f'"string", "subskill": "string (must match one of the given subskills exactly)", '
        f'"text": "string", "choices": ["string","string","string","string"], "correctAnswer": '
        f'"string (must exactly match one of the choices)"}}]}}'
    )
    return call_agent(SYSTEM_JSON_ONLY, user, max_tokens=1400)


def agent_evaluate_diagnostic(subject_name, topic_name, answered):
    user = (
        f"Subject: {subject_name}. Topic: {topic_name}. Diagnostic results: "
        f"{json.dumps(answered)}. For each subskill assign a starting mastery score 0-100 "
        f"(0 if wrong and clearly weak, 40-60 if wrong but close, 70+ if correct). Return "
        f'JSON exactly: {{"reasoning": "one to two sentences explaining the weakest area and '
        f'your plan", "mastery": {{"subskill name": number, ...}}, "startingDifficulty": '
        f'"easy" | "medium" | "hard"}}'
    )
    return call_agent(SYSTEM_JSON_ONLY, user)


def agent_next_question(subject_name, topic_name, mastery, difficulty):
    weakest = min(mastery, key=mastery.get)
    user = (
        f"Subject: {subject_name}. Topic: {topic_name}. Current mastery by subskill: "
        f"{json.dumps(mastery)}. Current difficulty: {difficulty}. Generate ONE multiple-"
        f'choice practice question focused on whichever subskill needs the most work (likely '
        f'"{weakest}"), at the given difficulty. If code is relevant, keep snippets short and '
        f'runnable. Return JSON exactly: {{"reasoning": "one sentence on why you picked this '
        f'subskill and difficulty", "subskill": "string", "difficulty": "easy"|"medium"|"hard", '
        f'"question": {{"text": "string", "choices": ["string","string","string","string"], '
        f'"correctAnswer": "string (must exactly match one choice)"}}}}'
    )
    return call_agent(SYSTEM_JSON_ONLY, user, max_tokens=1200)


def agent_grade_answer(question_text, subskill, correct_answer, student_answer, is_correct, difficulty):
    system = ("You are an expert, encouraging computer science tutor agent. Output ONLY "
              "valid JSON, no preamble, no markdown fences.")
    user = (
        f'Question: "{question_text}" Subskill: {subskill}. Correct answer: "{correct_answer}". '
        f'Student answered: "{student_answer}". Was correct: {is_correct}. Current difficulty: '
        f"{difficulty}. Write a short, warm, specific explanation (2-3 sentences). Then decide "
        f'the next difficulty level. Return JSON exactly: {{"reasoning": "one sentence on your '
        f'adaptation decision", "explanation": "string", "masteryDelta": number (positive if '
        f'correct, negative if wrong, between -15 and 15), "nextDifficulty": "easy"|"medium"|"hard"}}'
    )
    return call_agent(system, user)


# ---------------------------------------------------------------------------
# Persistence (simple JSON files, one per subject+topic)
# ---------------------------------------------------------------------------

def progress_key(subject_key, topic_key):
    return f"{subject_key}__{topic_key}"


def load_progress(subject_key, topic_key):
    path = PROGRESS_DIR / f"{progress_key(subject_key, topic_key)}.json"
    if path.exists():
        return json.loads(path.read_text())
    return None


def save_progress(subject_key, topic_key, mastery, difficulty):
    path = PROGRESS_DIR / f"{progress_key(subject_key, topic_key)}.json"
    path.write_text(json.dumps({"mastery": mastery, "difficulty": difficulty}))


def topic_overall_mastery(subject_key, topic_key):
    prior = load_progress(subject_key, topic_key)
    if not prior or not prior.get("mastery"):
        return None
    vals = list(prior["mastery"].values())
    return round(sum(vals) / len(vals)) if vals else None


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

def init_state():
    defaults = dict(
        screen="subject_select", subject=None, topic=None,
        notes=None, diagnostic_questions=[], diagnostic_answers={},
        mastery={}, difficulty="medium", current_question=None, answered=False,
        last_feedback=None, trail=[], questions_this_session=0, correct_this_session=0, streak=0,
    )
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def add_trail(phase, summary):
    st.session_state.trail.insert(0, {"phase": phase, "summary": summary})
    st.session_state.trail = st.session_state.trail[:6]


def go_to_subjects():
    st.session_state.screen = "subject_select"
    st.session_state.subject = None
    st.session_state.topic = None


def go_to_topics(subject_key):
    st.session_state.screen = "topic_select"
    st.session_state.subject = subject_key
    st.session_state.topic = None


def go_to_topic_hub(topic_key):
    st.session_state.screen = "topic_hub"
    st.session_state.topic = topic_key
    st.session_state.notes = None
    st.session_state.current_question = None
    st.session_state.answered = False
    st.session_state.last_feedback = None
    st.session_state.questions_this_session = 0
    st.session_state.correct_this_session = 0
    st.session_state.streak = 0


def start_practice():
    subject = SUBJECTS[st.session_state.subject]
    topic = subject["topics"][st.session_state.topic]
    prior = load_progress(st.session_state.subject, st.session_state.topic)
    if prior and prior.get("mastery"):
        st.session_state.mastery = prior["mastery"]
        st.session_state.difficulty = prior.get("difficulty", "medium")
        add_trail("Resume", f"Found prior progress for {topic['name']}. Picking up where the student left off.")
        with st.spinner("Choosing what to practice next..."):
            result = agent_next_question(subject["name"], topic["name"], st.session_state.mastery, st.session_state.difficulty)
        st.session_state.current_question = result
        add_trail("Generate", result["reasoning"])
        st.session_state.screen = "practice"
    else:
        st.session_state.mastery = {s: 0 for s in topic["subskills"]}
        with st.spinner("Building a quick diagnostic..."):
            result = agent_diagnose(subject["name"], topic)
        st.session_state.diagnostic_questions = result["questions"]
        st.session_state.diagnostic_answers = {}
        add_trail("Diagnose", result["reasoning"])
        st.session_state.screen = "diagnostic"


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Codeline — B.Tech CS Learning Agent", page_icon="\U0001F4D8", layout="wide")

st.markdown("""
<style>
.trail-node{border-left:2px dashed #E0A83E;padding-left:14px;margin-bottom:14px;}
.trail-phase{font-size:11px;text-transform:uppercase;letter-spacing:0.05em;color:#B5822A;font-weight:600;}
.trail-summary{font-size:13.5px;margin:2px 0 0;color:#333;}
.subskill-row{font-size:13px;margin-bottom:2px;}
.breadcrumb{font-size:13px;color:#888;margin-bottom:4px;}
</style>
""", unsafe_allow_html=True)

init_state()

st.title("\U0001F4D8 Codeline")
st.caption("Agentic study companion for B.Tech computer science · Python · Java · DBMS · DSA · Operating systems")

with st.sidebar:
    st.subheader("Agent trail")
    st.caption("The reasoning behind every decision, live.")
    if st.session_state.streak >= 2:
        st.success(f"\U0001F525 {st.session_state.streak} correct in a row")
    if not st.session_state.trail:
        st.caption("Pick a subject and topic and the agent's decisions will show up here.")
    for t in st.session_state.trail:
        st.markdown(
            f'<div class="trail-node"><div class="trail-phase">{t["phase"]}</div>'
            f'<div class="trail-summary">{t["summary"]}</div></div>',
            unsafe_allow_html=True,
        )
    if st.session_state.subject and st.session_state.topic and st.session_state.mastery:
        st.divider()
        topic_name = SUBJECTS[st.session_state.subject]["topics"][st.session_state.topic]["name"]
        st.subheader(f"Mastery — {topic_name}")
        for skill, pct in st.session_state.mastery.items():
            st.markdown(f'<div class="subskill-row">{skill} — {round(pct)}%</div>', unsafe_allow_html=True)
            st.progress(min(max(pct, 0), 100) / 100)
    if st.session_state.subject:
        st.divider()
        if st.button("Choose another subject", use_container_width=True):
            go_to_subjects()
            st.rerun()


# ---- subject select ----
if st.session_state.screen == "subject_select":
    st.subheader("Pick a subject")
    st.write("Each topic offers agent-generated study notes plus an adaptive practice loop "
             "that diagnoses gaps, plans a path, and adjusts difficulty as you go.")
    cols = st.columns(len(SUBJECTS))
    for i, (key, subj) in enumerate(SUBJECTS.items()):
        with cols[i]:
            st.markdown(f"### {subj['icon']} {subj['name']}")
            st.caption(f"{len(subj['topics'])} topics")
            if st.button("Open", key=f"subj_{key}", use_container_width=True):
                go_to_topics(key)
                st.rerun()


# ---- topic select ----
elif st.session_state.screen == "topic_select":
    subject = SUBJECTS[st.session_state.subject]
    st.markdown(f'<div class="breadcrumb">{subject["name"]}</div>', unsafe_allow_html=True)
    st.subheader(f"{subject['icon']} {subject['name']} — pick a topic")
    cols = st.columns(2)
    for i, (key, topic) in enumerate(subject["topics"].items()):
        with cols[i % 2]:
            with st.container(border=True):
                st.markdown(f"**{topic['name']}**")
                st.caption(", ".join(topic["subskills"]))
                overall = topic_overall_mastery(st.session_state.subject, key)
                if overall is not None:
                    st.caption(f"Last mastery: {overall}%")
                if st.button("Open topic", key=f"topic_{key}", use_container_width=True):
                    go_to_topic_hub(key)
                    st.rerun()
    if st.button("\u2190 Back to subjects"):
        go_to_subjects()
        st.rerun()


# ---- topic hub: study notes or practice ----
elif st.session_state.screen == "topic_hub":
    subject = SUBJECTS[st.session_state.subject]
    topic = subject["topics"][st.session_state.topic]
    st.markdown(f'<div class="breadcrumb">{subject["name"]} / {topic["name"]}</div>', unsafe_allow_html=True)
    st.subheader(topic["name"])
    st.caption("Covers: " + ", ".join(topic["subskills"]))

    c1, c2 = st.columns(2)
    if c1.button("\U0001F4D6 Read study notes", use_container_width=True, type="secondary"):
        with st.spinner("Writing study notes..."):
            st.session_state.notes = agent_generate_notes(subject["name"], topic["name"], topic["subskills"])
        st.rerun()
    if c2.button("\U0001F3AF Start adaptive practice", use_container_width=True, type="primary"):
        start_practice()
        st.rerun()

    if st.session_state.notes:
        notes = st.session_state.notes
        st.divider()
        st.markdown(f"**Overview**")
        st.write(notes["overview"])
        st.markdown("**Key concepts**")
        for concept in notes["keyConcepts"]:
            with st.expander(concept["title"]):
                st.write(concept["explanation"])
        if notes.get("example", {}).get("code"):
            st.markdown("**Example**")
            st.code(notes["example"]["code"], language=notes["example"].get("language", "text"))
            st.caption(notes["example"].get("explanation", ""))
        if notes.get("commonMistakes"):
            st.markdown("**Common mistakes**")
            for m in notes["commonMistakes"]:
                st.markdown(f"- {m}")

    if st.button("\u2190 Back to topics"):
        st.session_state.screen = "topic_select"
        st.rerun()


# ---- diagnostic ----
elif st.session_state.screen == "diagnostic":
    subject = SUBJECTS[st.session_state.subject]
    topic = subject["topics"][st.session_state.topic]
    st.markdown(f'<div class="breadcrumb">{subject["name"]} / {topic["name"]}</div>', unsafe_allow_html=True)
    st.subheader("Quick check-in")
    st.write("Answer these to help the agent see where to focus.")
    for i, q in enumerate(st.session_state.diagnostic_questions):
        st.caption(q["subskill"])
        answer = st.radio(f"{i+1}. {q['text']}", q["choices"], index=None, key=f"diag_{q['id']}")
        if answer:
            st.session_state.diagnostic_answers[q["id"]] = answer

    all_answered = len(st.session_state.diagnostic_answers) == len(st.session_state.diagnostic_questions)
    if st.button("Submit answers", disabled=not all_answered, type="primary"):
        answered = [
            {
                "subskill": q["subskill"],
                "question": q["text"],
                "studentAnswer": st.session_state.diagnostic_answers[q["id"]],
                "correctAnswer": q["correctAnswer"],
            }
            for q in st.session_state.diagnostic_questions
        ]
        with st.spinner("Scoring answers and planning a path..."):
            result = agent_evaluate_diagnostic(subject["name"], topic["name"], answered)
        st.session_state.mastery = result["mastery"]
        st.session_state.difficulty = result.get("startingDifficulty", "medium")
        add_trail("Plan", result["reasoning"])
        save_progress(st.session_state.subject, st.session_state.topic, st.session_state.mastery, st.session_state.difficulty)
        with st.spinner("Choosing what to practice next..."):
            next_q = agent_next_question(subject["name"], topic["name"], st.session_state.mastery, st.session_state.difficulty)
        st.session_state.current_question = next_q
        add_trail("Generate", next_q["reasoning"])
        st.session_state.screen = "practice"
        st.rerun()


# ---- practice ----
elif st.session_state.screen == "practice":
    subject = SUBJECTS[st.session_state.subject]
    topic = subject["topics"][st.session_state.topic]
    q = st.session_state.current_question
    st.markdown(f'<div class="breadcrumb">{subject["name"]} / {topic["name"]}</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([3, 1])
    c1.caption(q["subskill"])
    c2.caption(f"Difficulty: {q['difficulty']}")
    st.markdown(f"### {q['question']['text']}")

    if not st.session_state.answered:
        choice = st.radio("Choose one:", q["question"]["choices"], index=None, key=f"q_{id(q)}")
        if st.button("Submit answer", disabled=choice is None, type="primary"):
            is_correct = choice == q["question"]["correctAnswer"]
            st.session_state.answered = True
            with st.spinner("Reviewing the answer..."):
                try:
                    result = agent_grade_answer(
                        q["question"]["text"], q["subskill"], q["question"]["correctAnswer"],
                        choice, is_correct, q["difficulty"],
                    )
                    st.session_state.mastery[q["subskill"]] = max(0, min(100,
                        st.session_state.mastery.get(q["subskill"], 0) + result["masteryDelta"]))
                    st.session_state.difficulty = result["nextDifficulty"]
                    add_trail("Adapt", result["reasoning"])
                    st.session_state.last_feedback = {"is_correct": is_correct, "explanation": result["explanation"]}
                    save_progress(st.session_state.subject, st.session_state.topic, st.session_state.mastery, st.session_state.difficulty)
                except Exception:
                    st.session_state.last_feedback = {
                        "is_correct": is_correct,
                        "explanation": "Correct." if is_correct else "Not quite — take another look at the approach.",
                    }
            st.session_state.questions_this_session += 1
            if is_correct:
                st.session_state.correct_this_session += 1
                st.session_state.streak += 1
            else:
                st.session_state.streak = 0
            st.rerun()
    else:
        fb = st.session_state.last_feedback
        if fb["is_correct"]:
            st.success(f"**Correct.** {fb['explanation']}")
        else:
            st.error(f"**Not quite.** {fb['explanation']}")
        b1, b2 = st.columns(2)
        if b1.button("Next question", type="primary", use_container_width=True):
            st.session_state.answered = False
            st.session_state.last_feedback = None
            with st.spinner("Choosing what to practice next..."):
                next_q = agent_next_question(subject["name"], topic["name"], st.session_state.mastery, st.session_state.difficulty)
            st.session_state.current_question = next_q
            add_trail("Generate", next_q["reasoning"])
            st.rerun()
        if b2.button("End session", use_container_width=True):
            st.session_state.screen = "summary"
            st.rerun()


# ---- summary ----
elif st.session_state.screen == "summary":
    subject = SUBJECTS[st.session_state.subject]
    topic = subject["topics"][st.session_state.topic]
    st.subheader("Session complete")
    c1, c2, c3 = st.columns(3)
    c1.metric("Questions", st.session_state.questions_this_session)
    accuracy = round(st.session_state.correct_this_session / st.session_state.questions_this_session * 100) \
        if st.session_state.questions_this_session else 0
    c2.metric("Accuracy", f"{accuracy}%")
    c3.metric("Streak", st.session_state.streak)
    b1, b2, b3 = st.columns(3)
    if b1.button("Keep practicing", type="primary", use_container_width=True):
        st.session_state.questions_this_session = 0
        st.session_state.correct_this_session = 0
        st.session_state.screen = "practice"
        st.session_state.answered = False
        with st.spinner("Choosing what to practice next..."):
            next_q = agent_next_question(subject["name"], topic["name"], st.session_state.mastery, st.session_state.difficulty)
        st.session_state.current_question = next_q
        add_trail("Generate", next_q["reasoning"])
        st.rerun()
    if b2.button("Choose another topic", use_container_width=True):
        st.session_state.screen = "topic_select"
        st.rerun()
    if b3.button("Choose another subject", use_container_width=True):
        go_to_subjects()
        st.rerun()
