import os
import pickle
import socket
import uuid

import boto3
import streamlit as st
from streamlit_local_storage import LocalStorage

st.set_page_config(layout='wide')
local_storage = LocalStorage()

SESSION_KEY = 'session_id'
SESSION_CACHE_DIR = './session_data'

MODEL_KEYS = [
    'nova-pro',
    'nova-micro',
    'nova-lite',
]

os.makedirs(SESSION_CACHE_DIR, exist_ok=True)

session_data = {}


def _get_session_path(sid: str) -> str:
    return os.path.join(SESSION_CACHE_DIR, sid)


def get_or_restore_session() -> tuple[str, bool]:
    created = False

    _sid = (
        getattr(st.session_state, SESSION_KEY, None) or
        local_storage.getItem(SESSION_KEY)
    )

    sid = None
    if (
        _sid is not None and
        os.path.isfile(_get_session_path(_sid))
    ):
        sid = _sid
        # restore session variables from SESSION_CACHE_DIR
        with open(_get_session_path(sid), 'rb') as f:
            for key, value in pickle.load(f).items():
                session_data[key] = value
    if sid is None:
        # create a new session_id
        sid = str(uuid.uuid4())
        created = True

    st.session_state.session_id = sid
    local_storage.setItem(SESSION_KEY, sid)
    return sid, created


def persist_session():
    # save session variables to SESSION_CACHE_DIR
    with open(_get_session_path(st.session_state.session_id), 'wb') as f:
        data_to_pickle = {
            k: v
            for k, v in session_data.items()
        }
        pickle.dump(data_to_pickle, f)


def reset_session():
    sid = st.session_state.session_id
    path = _get_session_path(sid)
    if os.path.exists(path):
        os.remove(path)
    for key in list(session_data.keys()):
        del session_data[key]
    local_storage.deleteItem(SESSION_KEY)


def create_chat_completion_stream(
    model: str,
    messages: list,
):
    client = boto3.client('bedrock-runtime')

    streaming_response = client.converse_stream(
        modelId=model,
        messages=messages,
        inferenceConfig={'maxTokens': 5000},
    )

    def _streaming_response():
        # Extract and print the streamed response text in real-time.
        for chunk in streaming_response['stream']:
            if 'contentBlockDelta' in chunk:
                text = chunk['contentBlockDelta']['delta']['text']
                yield text

    return _streaming_response


session_id, new_session = get_or_restore_session()

with st.sidebar:
    st.title('LLM Bot @ AWS')
    st.markdown('Fully Scalable and Stateful with ECS behind ALB and EFS for session persistence')
    st.markdown(f'Hostname: `{socket.gethostname()}`')
    st.markdown(f'Session: `{session_id.split('-')[0]}`{' (new)' if new_session else ''}')

    # button to delete session if clicked
    if is_reset := st.button('Reset Session'):
        reset_session()

    model_name = st.selectbox(
        'Model',
        MODEL_KEYS,
        format_func=lambda x: x.replace('-', ' ').title(),
        index=MODEL_KEYS.index(session_data.get('model_name', MODEL_KEYS[0])),
    )
    session_data['model_name'] = model_name

if not is_reset:
    if 'messages' not in session_data:
        session_data['messages'] = []
    else:
        for message in session_data['messages']:
            with st.chat_message(message['role']):
                st.markdown(message['content'])

    if prompt := st.chat_input('What is up?', disabled=is_reset):
        session_data['messages'].append({
            'role': 'user',
            'content': prompt
        })
        with st.chat_message('user'):
            st.markdown(prompt)

        with st.chat_message('assistant'):
            stream = create_chat_completion_stream(
                model=f'amazon.{model_name}-v1:0',
                messages=[
                    {
                        'role': m['role'],
                        'content': [{
                            'text': m['content']
                        }]
                    }
                    for m in session_data['messages']
                ],
            )
            response = st.write_stream(stream)
        session_data['messages'].append({
            'role': 'assistant',
            'content': response
        })

    persist_session()
else:
    st.markdown(f'Session `{session_id}` has been reset, please refresh the page to start a new session.')
