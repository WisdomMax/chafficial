import subprocess

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"

js_code = """
async function run() {
  const tabs = await listBrowserTabs();
  const gptTab = tabs.find(t => t.url && t.url.includes('6ad7be96-e470-83e8-a5bf-1e8560f936e3'));
  const p = await attachBrowserTab(gptTab.targetId);

  const text = await p.evaluate(() => {
    // Canvas 에디터 요소 찾기
    const el = document.querySelector('[aria-label="작성을 시작하세요"]') ||
               document.querySelector('.canvas-content') ||
               document.querySelector('[contenteditable="true"]');
    return el ? el.innerText : "";
  });

  console.log('CANVAS_TEXT_START');
  console.log(text);
  console.log('CANVAS_TEXT_END');
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
if 'CANVAS_TEXT_START\n' in full and '\nCANVAS_TEXT_END' in full:
    content = full.split('CANVAS_TEXT_START\n')[1].split('\nCANVAS_TEXT_END')[0]
    with open("directive_045b_full.txt", "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[+] 성공: directive_045b_full.txt 저장 완료 ({len(content)}자)")
else:
    print("[-] 실패, stdout:", res.stdout[:300])
