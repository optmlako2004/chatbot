"""
Interface Gradio de TEST pour discuter avec le chatbot.

⚠️ Ce n'est PAS l'UI finale (ton coéquipier la fera en React).
C'est juste pour valider visuellement que le bot fonctionne.

Lancement :
    python ui_test.py
puis ouvre http://localhost:7860
"""

import uuid

import gradio as gr

from chatbot import build_agent, chat_with_trace

print("⏳ Chargement du chatbot...")
agent = build_agent()
print("✅ Prêt. Ouvre http://localhost:7860 dans ton navigateur.")


def respond(message, history, thread_id):
    if not thread_id:
        thread_id = str(uuid.uuid4())

    result = chat_with_trace(agent, message, thread_id=thread_id)
    answer = result["answer"]
    if result["tools_used"]:
        tools = ", ".join(set(result["tools_used"]))
        answer = f"_🔧 outils utilisés : {tools}_\n\n{answer}"

    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": answer},
    ]
    return "", history, thread_id


def reset(thread_id):
    return [], str(uuid.uuid4())


with gr.Blocks(title="Chatbot Finance — Test") as demo:
    gr.Markdown(
        "# 💰 Chatbot Finance (test)\n"
        "Pose-moi une question d'éducation financière. "
        "Pour les chiffres récents (taux, actualité), je cherche sur le web."
    )
    thread_state = gr.State(value=str(uuid.uuid4()))

    chatbot_ui = gr.Chatbot(type="messages", height=500, label="Conversation")
    msg = gr.Textbox(
        placeholder="Ta question... (ex: c'est quoi un livret A ?)",
        label="Message",
        autofocus=True,
    )

    with gr.Row():
        send_btn = gr.Button("Envoyer", variant="primary")
        reset_btn = gr.Button("🔄 Nouvelle conversation")

    gr.Examples(
        examples=[
            "C'est quoi un Livret A ?",
            "Quel est le taux du Livret A en 2026 ?",
            "Comment me protéger contre les arnaques bancaires ?",
            "Quelle est la différence entre PEL et CEL ?",
        ],
        inputs=msg,
    )

    msg.submit(respond, [msg, chatbot_ui, thread_state], [msg, chatbot_ui, thread_state])
    send_btn.click(respond, [msg, chatbot_ui, thread_state], [msg, chatbot_ui, thread_state])
    reset_btn.click(reset, [thread_state], [chatbot_ui, thread_state])


if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, inbrowser=False)
