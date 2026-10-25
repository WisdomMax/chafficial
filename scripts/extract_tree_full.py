import subprocess

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"

js_code = """
async function run() {
  const tabs = await listBrowserTabs();
  const gptTab = tabs.find(t => t.url && t.url.includes('6ad7be96-e470-83e8-a5bf-1e8560f936e3'));
  const p = await attachBrowserTab(gptTab.targetId);

  // snapshot with selector
  const s = await snapshot(p, { showHidden: true });
  console.log('SNAP_START');
  console.log(s.tree);
  console.log('SNAP_END');
}
await run();
"""

res = subprocess.run(
    ["/Users/wisdom/.local/bin/aside", "--profile", TARGET_PROFILE, "repl", js_code],
    capture_output=True,
    text=True,
    check=False
)

full = res.stdout
if 'SNAP_START\n' in full and '\nSNAP_END' in full:
    tree = full.split('SNAP_START\n')[1].split('\nSNAP_END')[0]
    with open("directive_045b_tree.txt", "w", encoding="utf-8") as f:
        f.write(tree)
    print(f"[+] 성공: directive_045b_tree.txt 저장 완료 ({len(tree)}자)")
else:
    print("[-] 실패, stdout:", res.stdout[:300])
