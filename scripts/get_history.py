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
  await sleep(6000);

  const res = await page.evaluate(() => {{
    // 모든 텍스트 단락 또는 article 조회
    const articles = Array.from(document.querySelectorAll('article, [data-message-author-role]'));
    if (articles.length === 0) {{
      return {{ count: 0, textSample: document.body.innerText.slice(0, 1000) }};
    }}
    return {{
      count: articles.length,
      messages: articles.map(a => a.innerText)
    }};
  }});

  console.log('RESULT_DATA:' + JSON.stringify(res));
}}
await run();
"""

res = subprocess.run(["/Users/wisdom/.local/bin/aside", "repl", js_code], check=False, capture_output=True, text=True)
for line in res.stdout.splitlines():
    if line.startswith("RESULT_DATA:"):
        data = json.loads(line[len("RESULT_DATA:"):])
        with open("chat_messages.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Extracted {data.get('count', 0)} messages.")
