import base64
import json
import uuid

import requests
import streamlit as st


DEFAULT_BACKEND_URL = "http://127.0.0.1:8000"


# This function creates the default values we want to keep in the Streamlit session.
def initialize_session_state() -> None:
    if "user_id" not in st.session_state:
        st.session_state.user_id = "user_demo"

    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())

    if "style" not in st.session_state:
        st.session_state.style = "default"

    if "backend_url" not in st.session_state:
        st.session_state.backend_url = DEFAULT_BACKEND_URL

    if "last_response" not in st.session_state:
        st.session_state.last_response = None

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0

    if "use_streaming" not in st.session_state:
        st.session_state.use_streaming = True

    if "draft_image_data_url" not in st.session_state:
        st.session_state.draft_image_data_url = None

    if "draft_image_name" not in st.session_state:
        st.session_state.draft_image_name = None


# This function builds the request body that will be sent to the FastAPI backend.
def build_chat_payload(message: str, image_url: str | None = None) -> dict:
    payload = {
        "message": message,
        "image_url": image_url,
        "context": {
            "user_id": st.session_state.user_id,
            "thread_id": st.session_state.thread_id,
            "style": st.session_state.style,
        },
    }
    return payload


# This function converts one uploaded file into a base64 data URL for the backend.
def build_image_data_url(uploaded_file) -> str | None:
    if uploaded_file is None:
        return None

    file_bytes = uploaded_file.getvalue()
    encoded_bytes = base64.b64encode(file_bytes).decode("utf-8")
    mime_type = uploaded_file.type or "image/png"
    return f"data:{mime_type};base64,{encoded_bytes}"


# This function sends the user message and optional image to the backend.
def call_chat_api(message: str, image_url: str | None = None) -> dict:
    response = requests.post(
        f"{st.session_state.backend_url}/chat",
        json=build_chat_payload(message, image_url=image_url),
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


# This function opens the streaming backend endpoint and yields SSE events one by one.
def stream_chat_api(message: str, image_url: str | None = None):
    with requests.post(
        f"{st.session_state.backend_url}/chat/stream",
        json=build_chat_payload(message, image_url=image_url),
        timeout=120,
        stream=True,
    ) as response:
        response.raise_for_status()

        current_event_name: str | None = None
        current_data_lines: list[str] = []

        for raw_line in response.iter_lines(decode_unicode=True):
            if raw_line is None:
                continue

            line = raw_line.strip()

            if not line:
                if current_event_name and current_data_lines:
                    data_text = "\n".join(current_data_lines)
                    yield {
                        "event": current_event_name,
                        "data": json.loads(data_text),
                    }

                current_event_name = None
                current_data_lines = []
                continue

            if line.startswith("event:"):
                current_event_name = line.removeprefix("event:").strip()
            elif line.startswith("data:"):
                current_data_lines.append(line.removeprefix("data:").strip())


# This function adds one user or assistant message to the Streamlit chat history.
def add_chat_message(
    role: str,
    content: str,
    response_data: dict | None = None,
    image_data_url: str | None = None,
) -> None:
    st.session_state.chat_messages.append(
        {
            "role": role,
            "content": content,
            "response_data": response_data,
            "image_data_url": image_data_url,
        }
    )


# This function clears the current frontend chat history.
def clear_chat_history() -> None:
    st.session_state.chat_messages = []
    st.session_state.last_response = None
    st.session_state.uploader_key += 1
    st.session_state.draft_image_data_url = None
    st.session_state.draft_image_name = None


# This function adds lightweight CSS so the app looks cleaner and more customer-facing.
def apply_custom_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top left, #fff4dd 0%, transparent 28%),
                radial-gradient(circle at top right, #dff3ff 0%, transparent 24%),
                linear-gradient(180deg, #fffdf8 0%, #f7f3eb 100%);
        }
        .block-container {
            max-width: 980px;
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        .hero-card {
            background: rgba(255, 255, 255, 0.76);
            border: 1px solid rgba(26, 26, 26, 0.08);
            border-radius: 24px;
            padding: 1.4rem 1.4rem 1.1rem 1.4rem;
            box-shadow: 0 18px 40px rgba(91, 74, 42, 0.08);
            backdrop-filter: blur(10px);
            margin-bottom: 1rem;
        }
        .hero-eyebrow {
            font-size: 0.8rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #7d6640;
            margin-bottom: 0.35rem;
            font-weight: 700;
        }
        .hero-title {
            font-size: 2.7rem;
            line-height: 1.05;
            color: #1e1d1a;
            margin: 0;
            font-weight: 800;
        }
        .hero-subtitle {
            color: #5c584f;
            margin-top: 0.55rem;
            margin-bottom: 0;
            font-size: 1rem;
        }
        .composer-card {
            background: rgba(255, 255, 255, 0.9);
            border: 1px solid rgba(26, 26, 26, 0.08);
            border-radius: 22px;
            padding: 1rem 1rem 0.4rem 1rem;
            box-shadow: 0 12px 28px rgba(91, 74, 42, 0.06);
            margin-bottom: 1rem;
        }
        .tiny-label {
            font-size: 0.82rem;
            color: #70695a;
            font-weight: 600;
            margin-bottom: 0.35rem;
        }
        .status-chip {
            display: inline-block;
            padding: 0.35rem 0.7rem;
            border-radius: 999px;
            background: #f1ead9;
            color: #6e5a2d;
            font-size: 0.82rem;
            font-weight: 700;
        }
        .empty-state {
            text-align: center;
            padding: 2.8rem 1rem 1.2rem 1rem;
            color: #716b61;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# This function draws the top hero area and the simple customer-facing controls.
def render_header() -> None:
    left_col, right_col = st.columns([0.8, 0.2], vertical_alignment="center")

    with left_col:
        st.markdown(
            """
            <div class="hero-card">
                <h1 class="hero-title">Multimodal Assistant</h1>
                <p class="hero-subtitle">
                    Ask a question, upload an image, and get a clear answer in one place.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right_col:
        if st.button("New chat", use_container_width=True):
            st.session_state.thread_id = str(uuid.uuid4())
            clear_chat_history()
            st.rerun()

        st.selectbox(
            "Response style",
            options=["default", "expert", "child"],
            key="style",
            label_visibility="collapsed",
        )


# This function stores the currently selected image draft for the next outgoing message.
def update_draft_image(uploaded_file) -> None:
    if uploaded_file is None:
        st.session_state.draft_image_data_url = None
        st.session_state.draft_image_name = None
        return

    st.session_state.draft_image_data_url = build_image_data_url(uploaded_file)
    st.session_state.draft_image_name = uploaded_file.name


# This function shows extra backend details for one assistant message.
def render_response_details(response_data: dict | None) -> None:
    if not response_data:
        return

    if response_data.get("request_type") == "weather" and response_data.get("weather"):
        weather = response_data["weather"]
        st.caption(
            f"{weather['location']} • {weather['temperature']}° • {weather['summary']}"
        )

    if response_data.get("image_analysis"):
        image_analysis = response_data["image_analysis"]
        if image_analysis.get("detected_objects"):
            st.caption(
                "Detected: " + ", ".join(image_analysis["detected_objects"])
            )


# This function turns backend progress steps into short customer-friendly status text.
def get_friendly_status_text(step: str) -> str | None:
    status_map = {
        "memory_loaded": "Recalling the conversation...",
        "context_ready": "Preparing the answer...",
        "model": "Writing the answer...",
        "tools": "Checking live information...",
        "agent": "Thinking...",
    }
    return status_map.get(step)


# This function draws the whole chat history using Streamlit chat components.
def render_chat_history() -> None:
    if not st.session_state.chat_messages:
        st.markdown(
            """
            <div class="empty-state">
                Start with a question like “What is the weather in Mumbai?” or upload an image and ask what it shows.
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            if message.get("image_data_url"):
                st.image(message["image_data_url"], width=240)

            st.write(message["content"])

            if message["role"] == "assistant":
                render_response_details(message.get("response_data"))


# This function lets the user upload one image and preview it before sending.
def render_image_uploader():
    st.markdown('<div class="composer-card">', unsafe_allow_html=True)
    st.markdown('<div class="tiny-label">Add an image</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Add an image",
        type=["png", "jpg", "jpeg", "webp"],
        key=f"image_uploader_{st.session_state.uploader_key}",
        label_visibility="collapsed",
    )
    update_draft_image(uploaded_file)

    if uploaded_file is not None:
        st.image(uploaded_file, width=220)
        st.markdown(
            f'<span class="status-chip">{st.session_state.draft_image_name}</span>',
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    return uploaded_file


# This function sends the current message and optional image to the backend.
def handle_user_message(message: str, uploaded_file=None) -> None:
    image_data_url = build_image_data_url(uploaded_file)
    add_chat_message("user", message, image_data_url=image_data_url)

    with st.spinner("Calling backend..."):
        try:
            response_data = call_chat_api(message, image_url=image_data_url)
            st.session_state.last_response = response_data
            assistant_text = response_data.get("answer", "I did not receive an answer.")
            add_chat_message("assistant", assistant_text, response_data=response_data)
            st.session_state.uploader_key += 1
            st.session_state.draft_image_data_url = None
            st.session_state.draft_image_name = None
        except requests.exceptions.RequestException as exc:
            error_text = f"Backend request failed: {exc}"
            st.session_state.last_response = None
            add_chat_message("assistant", error_text, response_data=None)


# This function handles one streamed request and updates the UI live while events arrive.
def handle_user_message_streaming(message: str, uploaded_file=None) -> None:
    image_data_url = build_image_data_url(uploaded_file)
    add_chat_message("user", message, image_data_url=image_data_url)

    with st.chat_message("assistant"):
        progress_box = st.empty()
        answer_box = st.empty()
        details_box = st.empty()

        streamed_text = ""
        final_response: dict | None = None

        try:
            for event in stream_chat_api(message, image_url=image_data_url):
                event_name = event["event"]
                event_data = event["data"]

                if event_name == "metadata":
                    progress_box.caption("Starting response...")

                elif event_name == "progress":
                    step = event_data.get("step", "working")
                    friendly_text = get_friendly_status_text(step)
                    if friendly_text:
                        progress_box.caption(friendly_text)

                elif event_name == "token":
                    streamed_text += event_data.get("text", "")
                    answer_box.write(streamed_text)

                elif event_name == "final":
                    final_response = event_data
                    final_answer = final_response.get("answer", streamed_text)
                    if final_answer:
                        streamed_text = final_answer
                        answer_box.write(streamed_text)

                    progress_box.empty()

                    with details_box.container():
                        render_response_details(final_response)

                elif event_name == "error":
                    error_text = event_data.get("message", "Unknown streaming error.")
                    progress_box.empty()
                    streamed_text = error_text
                    answer_box.write(streamed_text)

            st.session_state.last_response = final_response
            add_chat_message("assistant", streamed_text, response_data=final_response)
            st.session_state.uploader_key += 1
            st.session_state.draft_image_data_url = None
            st.session_state.draft_image_name = None

        except requests.exceptions.RequestException as exc:
            error_text = f"Backend streaming request failed: {exc}"
            progress_box.error(error_text)
            answer_box.write(error_text)
            st.session_state.last_response = None
            add_chat_message("assistant", error_text, response_data=None)


# This function builds the main page and handles the send button action.
def main() -> None:
    st.set_page_config(
        page_title="Multimodal Assistant",
        page_icon="AI",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    initialize_session_state()
    apply_custom_styles()
    render_header()

    uploaded_file = render_image_uploader()
    render_chat_history()

    message = st.chat_input("Message the assistant")
    if message:
        if st.session_state.use_streaming:
            handle_user_message_streaming(message.strip(), uploaded_file=uploaded_file)
        else:
            handle_user_message(message.strip(), uploaded_file=uploaded_file)
        st.rerun()


if __name__ == "__main__":
    main()
