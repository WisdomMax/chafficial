import json
import subprocess

target_url = "https://chatgpt.com/c/6ad7be96-e470-83e8-a5bf-1e8560f936e3"

js_code = f"""
async function run() {{
  const targetUrl = {json.dumps(target_url)};
  const tabs = await listBrowserTabs();
  const gptTab = tabs.find(t => t.url && t.url.includes(targetUrl.split('/').pop()));
  if (gptTab) {{
    await attachBrowserTab(gptTab.targetId);
  }} else {{
    await openTab(targetUrl);
  }}
  await sleep(3000);

  const fullText = await page.evaluate(() => document.body.innerText);
  console.log('FULL_BODY_TEXT_START');
  console.log(fullText);
  console.log('FULL_BODY_TEXT_END');
}}
await run();
"""

res = subprocess.run(["/Users/wisdom/.local/bin/aside", "repl", js_code], check=False, capture_output=True, text=True)
with open("chatgpt_full_thread.txt", "w", encoding="utf-8") as f:
    f.write(res.stdout)
print(f"Dumped {len(res.stdout)} chars to chatgpt_full_thread.txt")
