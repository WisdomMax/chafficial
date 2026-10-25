import json
import subprocess

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
NEW_URL = "https://chatgpt.com/c/6ade5dae-1c94-83ee-acf8-d6058171a94d"

js_code = f"""
async function run() {{
  const page = await attachActiveBrowserTab();
  await page.goto('{NEW_URL}');
  await sleep(4000);
  console.log('PAGE_TITLE:' + await page.title());
  console.log('PAGE_URL:' + await page.url());
  const info = await page.evaluate(() => {{
    const pms = Array.from(document.querySelectorAll('div.ProseMirror'));
    const promptEl = document.querySelector('#prompt-textarea');
    return {{
      has_input: Boolean(pms.length > 0 || promptEl),
      body_snippet: document.body.innerText.slice(-1500)
    }};
  }});
  console.log('INPUT_ACTIVE:' + info.has_input);
  console.log('BODY_SNIPPET:\\n' + info.body_snippet);
}}
await run();
"""

res = subprocess.run(
    ["/Users/wisdom/.local/bin/aside", "--profile", TARGET_PROFILE, "repl", js_code],
    capture_output=True,
    text=True,
    check=False,
)

print(res.stdout)
