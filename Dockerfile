FROM python:3.13-slim
# Wheels for some pypi packages are not available for py3.13 yet

RUN groupadd --system streamlit && useradd --system --gid streamlit streamlit && \
    mkdir -p /app/session_state /home/streamlit && \
    chown -R streamlit:streamlit /app /app/session_state /home/streamlit

WORKDIR /app

ADD .streamlit /home/streamlit/.streamlit
ADD chatbot.py requirements.txt ./

RUN pip install --upgrade pip && \
    pip install -r requirements.txt --no-cache-dir && \
    rm requirements.txt

USER streamlit

EXPOSE 8501

CMD ["python3", "-m", "streamlit", "run", "./chatbot.py"]
