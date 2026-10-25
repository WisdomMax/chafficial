import subprocess

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"

js_code = """
async function run() {
  const tabs = await listBrowserTabs();
  const gptTab = tabs.find(t => t.url && t.url.includes('6ad7be96-e470-83e8-a5bf-1e8560f936e3'));
  const p = await attachBrowserTab(gptTab.targetId);

  const s = await snapshot(p);
  console.log('TREE_LEN:' + s.tree.length);
  console.log('TREE_TAIL:');
  console.log(s.tree.slice(-4000));
}
await run();
"""

res = subprocess.run(
    ["/Users/wisdom/.local/bin/aside", "--profile", TARGET_PROFILE, "repl", js_code],
    capture_output=True,
    text=True,
    check=False
)

for line in res.stdout.splitlines():
    if "TREE_LEN:" in line or "TREE_TAIL:" in line or "감사" in line or "판정" in line or "승인" in line:
        print(line[:200])
