from src.llm_agent import extract_negotiation_request


customer_message = (
    "I'll take the speaker, cable and laptop stand. "
    "Can you give me a good deal?"
)


result = extract_negotiation_request(
    customer_message
)


print("\n===== CUSTOMER MESSAGE =====")
print(customer_message)

print("\n===== GEMINI EXTRACTION =====")
print(result)

print("\n===== DATA TYPE =====")
print(type(result))