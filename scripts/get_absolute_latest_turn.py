#!/usr/bin/env python3
import json
import subprocess

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
CHATGPT_URL = "https://chatgpt.com/c/6ae25099-daa0-83e8-8efd-08ef73499525?no_universal_links=1"

js_code = f"""
const p = await openTab({json.dumps(CHATGPT_URL)});
await sleep(4000);

const result = await p.evaluate(() => {{
  // 대화창 내의 모든 메시지 턴을 찾는다
  const turns = Array.from(document.querySelectorAll('[data-message-author-role], div.agent-turn, div[class*="conversation-item"], [data-testid^="conversation-turn-"]'));
  
  // 전체 본문 텍스트의 마지막 15,000자
  const main = document.querySelector('main');
  const fullText = main ? main.innerText : document.body.innerText;
  
  return {{
    turnCount: turns.length,
    lastTurns: turns.slice(-3).map(t => t.innerText),
    tail: fullText.slice(-10000)
  }};
}});

console.log('===FULL_TAIL_START===');
console.log(result.tail);
console.log('===FULL_TAIL_END===');
"""

res = subprocess.run([
    "/Users/wisdom/.local/bin/aside",
    "--profile", TARGET_PROFILE,
    "exec", js_code
], capture_output=True, text=True)

out = res.stdout or ""
with open("reports/LATEST_CHATGPT_TAIL.txt", "w", encoding="utf-8") as f:
    f.write(out)

if "===FULL_TAIL_START===" in out:
    content = out.split("===FULL_TAIL_START===")[1].split("===FULL_TAIL_END===")[0].strip()
    print("Fetched successfully! Length:", len(content))
    with open("reports/CLEANED_LATEST_TAIL.txt", "w", encoding="utf-8") as f:
        f.write(content)
    print("\n--- LAST 1000 CHARACTERS ---")
    print(content[-1000:])
else:
    print("Could not find delimiter. STDOUT preview:")
    print(out[:500])
