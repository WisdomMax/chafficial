import subprocess

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"

js_code = """
async function run() {
  const tabs = await listBrowserTabs();
  const gptTab = tabs.find(t => t.url && t.url.includes('6ad7be96-e470-83e8-a5bf-1e8560f936e3'));
  const p = await attachBrowserTab(gptTab.targetId);

  const s = await snapshot(p);
  console.log('SNAP_LEN:' + s.tree.length);
  console.log('SNAP_TAIL:');
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

with open("snap_045c.txt", "w", encoding="utf-8") as f:
    f.write(res.stdout)

for line in res.stdout.splitlines():
    if "SNAP_LEN:" in line or "DIRECTIVE 045-C" in line:
        print(line[:200])
