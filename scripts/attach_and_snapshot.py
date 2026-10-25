import subprocess
import json

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"

js_code = """
async function run() {
  const tabs = await listBrowserTabs();
  console.log('BROWSER_TABS:' + JSON.stringify(tabs.map(t => ({ targetId: t.targetId, active: t.active, title: t.title, url: t.url }))));

  // chatgpt 탭 찾기
  const gptTab = tabs.find(t => t.url && t.url.includes('chatgpt.com'));
  if (gptTab) {
    const page = await attachBrowserTab(gptTab.targetId);
    console.log('ATTACHED_TO:' + gptTab.title + ' (' + gptTab.url + ')');
    const s = await snapshot(page);
    console.log('SNAPSHOT_TREE_LEN:' + s.tree.length);
    // 트리 내용의 마지막 4000자
    console.log('SNAPSHOT_TAIL:');
    console.log(s.tree.slice(-4000));
  } else {
    console.log('NO_CHATGPT_TAB_FOUND');
  }
}
await run();
"""

res = subprocess.run(
    ["/Users/wisdom/.local/bin/aside", "--profile", TARGET_PROFILE, "repl", js_code],
    capture_output=True,
    text=True,
    check=False
)

with open("aside_snapshot_output.txt", "w", encoding="utf-8") as f:
    f.write(res.stdout)

for line in res.stdout.splitlines():
    if "BROWSER_TABS:" in line or "ATTACHED_TO:" in line or "SNAPSHOT_TREE_LEN:" in line:
        print(line[:200])
