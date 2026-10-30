#!/usr/bin/env python3
import json
import subprocess

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
CHATGPT_URL = "https://chatgpt.com/c/6ae25099-daa0-83e8-8efd-08ef73499525?no_universal_links=1"

js_code = f"""
const p = await openTab({json.dumps(CHATGPT_URL)});
await sleep(4000);

const text = await p.evaluate(() => {{
  const articles = Array.from(document.querySelectorAll('article'));
  if (articles.length >= 2) {{
    // 마지막 2개 아티클 텍스트
    return articles.slice(-2).map(a => a.innerText).join('\\n--- ARTICLE BREAK ---\\n');
  }}
  const main = document.querySelector('main');
  return main ? main.innerText.slice(-6000) : document.body.innerText.slice(-6000);
}});

console.log('===REPLY_CHUNK_START===');
console.log(text);
console.log('===REPLY_CHUNK_END===');
"""

res = subprocess.run([
    "/Users/wisdom/.local/bin/aside",
    "--profile", TARGET_PROFILE,
    "exec", js_code
], capture_output=True, text=True)

out = res.stdout or ""
with open("reports/CHATGPT_LATEST_TURN.txt", "w", encoding="utf-8") as f:
    f.write(out)

if "===REPLY_CHUNK_START===" in out:
    content = out.split("===REPLY_CHUNK_START===")[1].split("===REPLY_CHUNK_END===")[0].strip()
    print("SUCCESS! Length:", len(content))
    print(content)
else:
    print("Snippet:", out[-1000:])
