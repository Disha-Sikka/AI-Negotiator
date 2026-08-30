from src.llm_agent import ask_gemini


message = """
You are an online shopping negotiation assistant.

A customer says:

"I'm buying 5 USB-C cables. Can you give me a better price?"

Reply naturally in one sentence.
"""


response = ask_gemini(message)

print("\n===== GEMINI RESPONSE =====")
print(response)