import chainlit as cl
import openai
import requests

openai.api_key = 'sk-proj-yhpeTV54tuAmi1TbOyNHT3BlbkFJMwyYoQFtyXPg86UCmDeJ'


@cl.on_chat_start
def on_chat_start():
    cl.user_session.set("hist", "")


@cl.on_message
async def on_message(message: cl.Message):
    hist = cl.user_session.get("hist")

    params = {
        "text": message.content,
    }

    url = 'http://localhost:4000/chat'

    try:
        x = requests.post(url, json=params)
        x.raise_for_status()
        response_text = x.text
    except requests.RequestException as e:
        response_text = f"Fehler bei der Anfrage: {e}"

    cl.user_session.set("hist", hist + ' ' + response_text)

    await cl.Message(content=response_text).send()


if __name__ == "__main__":
    from chainlit.cli import run_chainlit

    run_chainlit("frontend.py")
