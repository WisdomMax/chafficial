import subprocess

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"

js_code = """
async function run() {
  const tabs = await listBrowserTabs();
  const gptTab = tabs.find(t => t.url && t.url.includes('6ad7be96-e470-83e8-a5bf-1e8560f936e3'));
  const p = await attachBrowserTab(gptTab.targetId);

  // Canvas 에디터 열기 또는 텍스트 확인
  const text = await p.evaluate(() => {
    const els = Array.from(document.querySelectorAll('*'));
    for (const el of els) {
      if (el.innerText && el.innerText.startsWith('CHA-FICIAL DIRECTIVE 045-C')) {
        return el.innerText;
      }
    }
    // 없으면 body에서 찾기
    const body = document.body.innerText;
    const idx = body.indexOf('CHA-FICIAL DIRECTIVE 045-C');
    if (idx !== -1) {
      return body.slice(idx);
    }
    return "";
  });

  console.log('045C_LEN:' + text.length);
  console.log('---START---');
  console.log(text);
  console.log('---END---');
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
if '---START---\n' in full and '\n---END---' in full:
    content = full.split('---START---\n')[1].split('\n---END---')[0]
    with open("directive_045c_full.txt", "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[+] 성공: directive_045c_full.txt 저장 완료 ({len(content)}자)")
else:
    print("[-] 실패, stdout:", res.stdout[:300])
