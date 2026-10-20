with open("chatgpt_full_thread.txt", "r", encoding="utf-8") as f:
    text = f.read()

idx = text.find("DIRECTIVE 002-C")
if idx != -1:
    print(f"Found DIRECTIVE 002-C at index {idx}")
    end_idx = text.find("카피셜 완료", idx)
    if end_idx != -1:
        extracted = text[idx-50:end_idx+50]
    else:
        extracted = text[idx-50:idx+4000]
    with open("DIRECTIVE_002C.md", "w", encoding="utf-8") as out:
        out.write(extracted)
    print("Saved to DIRECTIVE_002C.md")
else:
    print("DIRECTIVE 002-C not found directly, searching '002-C'...")
    idx2 = text.find("002-C")
    while idx2 != -1:
        print(f"Found '002-C' at {idx2}: {text[idx2-30:idx2+70]}")
        idx2 = text.find("002-C", idx2+1)
