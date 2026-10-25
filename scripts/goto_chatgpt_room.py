import subprocess
import json

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
TARGET_ROOM_URL = "https://chatgpt.com/c/6ad7be96-e470-83e8-a5bf-1e8560f936e3"

js_code = """
async function run() {
  const tabs = await listBrowserTabs();
  const gptTab = tabs.find(t => t.url && t.url.includes('chatgpt.com'));
  if (!gptTab) {
    console.log('NO_TAB');
    return;
  }

  const p = await attachBrowserTab(gptTab.targetId);
  console.log('ATTACHED_TO:' + gptTab.title);

  await p.goto('""" + TARGET_ROOM_URL + """');
  await sleep(6000);

  // 로딩 확인
  const title = await p.title();
  const url = await p.url();
  console.log('LOADED_URL:' + url);
  console.log('LOADED_TITLE:' + title);

  // 스냅샷
  const s = await snapshot(p);
  console.log('TREE_LEN:' + s.tree.length);
  return s.tree;
}
await run();
"""

res = subprocess.run(
    ["/Users/wisdom/.local/bin/aside", "--profile", TARGET_PROFILE, "repl", js_code],
    capture_output=True,
    text=True,
    check=False
)

with open("gpt_room_snapshot.txt", "w", encoding="utf-8") as f:
    f.write(res.stdout)

for line in res.stdout.splitlines():
    if any(k in line for k in ["ATTACHED_TO:", "LOADED_URL:", "LOADED_TITLE:", "TREE_LEN:"]):
        print(line)
