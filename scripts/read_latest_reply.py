#!/usr/bin/env python3
import json
import subprocess

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
CHATGPT_URL = "https://chatgpt.com/c/6ae25099-daa0-83e8-8efd-08ef73499525?no_universal_links=1"

js_code = f"""
const p = await openTab({json.dumps(CHATGPT_URL)});
await sleep(3000);

const text = await p.evaluate(() => {{
  const articles = Array.from(document.querySelectorAll('article'));
  if (articles.length === 0) return document.body.innerText.slice(-3000);
  return articles[articles.length - 1].innerText;
}});

console.log('REPLY_TEXT_START');
console.log(text);
console.log('REPLY_TEXT_END');
"""

res = subprocess.run([
    "/Users/wisdom/.local/bin/aside",
    "--profile", TARGET_PROFILE,
    "exec", js_code
], capture_output=True, text=True)

out = res.stdout or ""
with open("reports/LATEST_CHATGPT_REPLY.txt", "w", encoding="utf-8") as f:
    f.write(out)

if "REPLY_TEXT_START" in out and "REPLY_TEXT_END" in out:
    content = out.split("REPLY_TEXT_START")[1].split("REPLY_TEXT_END")[0].strip()
    print("SUCCESS! Length:", len(content))
    print(content[:600])
else:
    print("Snippet:", out[:300])
