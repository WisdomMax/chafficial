import subprocess

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"

js_code = """
async function run() {
  const tabs = await listBrowserTabs();
  const gptTab = tabs.find(t => t.url && t.url.includes("6ad7be96-e470-83e8-a5bf-1e8560f936e3"));
  const p = await attachBrowserTab(gptTab.targetId);

  const s = await snapshot(p);
  console.log("SNAPSHOT_FULL_START");
  console.log(s.tree);
  console.log("SNAPSHOT_FULL_END");
}
await run();
"""

res = subprocess.run(
    ["/Users/wisdom/.local/bin/aside", "--profile", TARGET_PROFILE, "repl", js_code],
    capture_output=True,
    text=True
)

with open("latest_tree.txt", "w", encoding="utf-8") as f:
    f.write(res.stdout)

print(f"tree saved, total length: {len(res.stdout)}")
