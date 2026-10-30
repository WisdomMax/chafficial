#!/usr/bin/env python3
import json
import subprocess

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
CHATGPT_URL = "https://chatgpt.com/c/6ae25099-daa0-83e8-8efd-08ef73499525?no_universal_links=1"

js_code = f"""
const p = await openTab({json.dumps(CHATGPT_URL)});
await sleep(3500);

const text = await p.evaluate(() => {{
  const articles = Array.from(document.querySelectorAll('article'));
  if (articles.length >= 2) {{
    return articles.slice(-2).map(a => a.innerText).join('\\n--- ARTICLE BREAK ---\\n');
  }}
  const main = document.querySelector('main');
  return main ? main.innerText.slice(-6000) : document.body.innerText.slice(-6000);
}});

console.log('===DIRECTIVE_097_FEEDBACK_START===');
console.log(text);
console.log('===DIRECTIVE_097_FEEDBACK_END===');
"""

res = subprocess.run([
    "/Users/wisdom/.local/bin/aside",
    "--profile", TARGET_PROFILE,
    "exec", js_code
], capture_output=True, text=True)

out = res.stdout or ""
with open("reports/CHATGPT_097_FEEDBACK.txt", "w", encoding="utf-8") as f:
    f.write(out)

if "===DIRECTIVE_097_FEEDBACK_START===" in out:
    content = out.split("===DIRECTIVE_097_FEEDBACK_START===")[1].split("===DIRECTIVE_097_FEEDBACK_END===")[0].strip()
    print("SUCCESS! Content length:", len(content))
    print("\n--- SNIPPET ---")
    print(content[-1500:])
else:
    print("Snippet:", out[-500:])
