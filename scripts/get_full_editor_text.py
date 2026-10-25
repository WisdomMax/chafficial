import subprocess

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"

js_code = """
async function run() {
  const tabs = await listBrowserTabs();
  const gptTab = tabs.find(t => t.url && t.url.includes('6ad7be96-e470-83e8-a5bf-1e8560f936e3'));
  const p = await attachBrowserTab(gptTab.targetId);

  const loc = p.locator('[aria-label="작성을 시작하세요"]');
  const count = await loc.count();
  console.log('LOCATOR_COUNT:' + count);
  if (count > 0) {
    const text = await loc.innerText();
    console.log('TEXT_LEN:' + text.length);
    console.log('DIRECTIVE_START');
    console.log(text);
    console.log('DIRECTIVE_END');
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

full = res.stdout
if 'DIRECTIVE_START\n' in full and '\nDIRECTIVE_END' in full:
    content = full.split('DIRECTIVE_START\n')[1].split('\nDIRECTIVE_END')[0]
    with open("directive_045b_complete.txt", "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[+] 성공: directive_045b_complete.txt 저장 완료 ({len(content)}자)")
else:
    print("[-] 추출 실패 stdout:", res.stdout[:300])
