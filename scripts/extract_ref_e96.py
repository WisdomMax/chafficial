import subprocess

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"

js_code = """
async function run() {
  const tabs = await listBrowserTabs();
  const gptTab = tabs.find(t => t.url && t.url.includes('6ad7be96-e470-83e8-a5bf-1e8560f936e3'));
  const p = await attachBrowserTab(gptTab.targetId);

  // e96 로케이터의 innerText 가져오기
  const loc = p.locator('e96');
  const text = await loc.innerText();
  console.log('LOC_TEXT_START');
  console.log(text);
  console.log('LOC_TEXT_END');
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
if 'LOC_TEXT_START\n' in full and '\nLOC_TEXT_END' in full:
    content = full.split('LOC_TEXT_START\n')[1].split('\nLOC_TEXT_END')[0]
    with open("directive_045b_full.txt", "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[+] 성공: directive_045b_full.txt 저장 완료 ({len(content)}자)")
else:
    print("[-] 실패, stdout:", res.stdout[:300])
