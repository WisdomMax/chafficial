import subprocess

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"

js_code = """
async function run() {
  const tabs = await listBrowserTabs();
  const gptTab = tabs.find(t => t.url && t.url.includes('6ad7be96-e470-83e8-a5bf-1e8560f936e3'));
  if (!gptTab) {
    console.log('NO_TAB');
    return;
  }

  const p = await attachBrowserTab(gptTab.targetId);
  const s = await snapshot(p);
  console.log('TREE_START');
  console.log(s.tree);
  console.log('TREE_END');
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
if 'TREE_START\n' in full and '\nTREE_END' in full:
    tree = full.split('TREE_START\n')[1].split('\nTREE_END')[0]
    with open("chatgpt_accessibility_tree.txt", "w", encoding="utf-8") as f:
        f.write(tree)
    print(f"[+] 성공: chatgpt_accessibility_tree.txt 저장 완료 ({len(tree)}자)")
else:
    with open("chatgpt_accessibility_tree.txt", "w", encoding="utf-8") as f:
        f.write(full)
    print(f"[-] 태그 미발견, 전체 저장 ({len(full)}자)")
