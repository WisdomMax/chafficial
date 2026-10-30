#!/usr/bin/env python3
import json
import subprocess

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"

js_code = """
const tabs = await listBrowserTabs();
const chatTab = tabs.find(t => (t.url || '').includes('6ae25099-daa0-83e8-8efd-08ef73499525'));

if (!chatTab) {
  console.log('[!] No ChatGPT tab found!');
} else {
  const tid = chatTab.targetId || chatTab.id;
  const p = await attachBrowserTab(tid);
  await sleep(2500);

  const text = await p.evaluate(() => {
    const main = document.querySelector('main');
    return main ? main.innerText.slice(-10000) : document.body.innerText.slice(-10000);
  });

  console.log('===EXISTING_TAB_TAIL_START===');
  console.log(text);
  console.log('===EXISTING_TAB_TAIL_END===');
}
"""

res = subprocess.run([
    "/Users/wisdom/.local/bin/aside",
    "--profile", TARGET_PROFILE,
    "exec", js_code
], capture_output=True, text=True)

out = res.stdout or ""
with open("reports/EXISTING_TAB_FEEDBACK.txt", "w", encoding="utf-8") as f:
    f.write(out)

if "===EXISTING_TAB_TAIL_START===" in out:
    content = out.split("===EXISTING_TAB_TAIL_START===")[1].split("===EXISTING_TAB_TAIL_END===")[0].strip()
    print("SUCCESS! Content length:", len(content))
    with open("reports/CLEANED_EXISTING_TAB_FEEDBACK.txt", "w", encoding="utf-8") as f:
        f.write(content)
    print("\n--- SNIPPET ---")
    print(content[-1500:])
else:
    print("No delimiter. Output preview:", out[:500])
