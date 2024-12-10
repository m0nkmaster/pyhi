import pvporcupine

print("Available Porcupine wake words:")
for keyword in sorted(pvporcupine.KEYWORDS):
    print(f"- {keyword}")
