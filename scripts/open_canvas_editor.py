import subprocess

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"

js_code = """
async function run() {
  const tabs = await listBrowserTabs();
  const gptTab = tabs.find(t => t.url && t.url.includes('6ad7be96-e470-83e8-a5bf-1e8560f936e3'));
  const p = await attachBrowserTab(gptTab.targetId);

  // '편집기 열기' 버튼 클릭
  const clicked = await p.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const openBtn = btns.find(b => b.innerText.includes('편집기 열기') || (b.getAttribute('aria-label') && b.getAttribute('aria-label').includes('편집기')));
    if (openBtn) {
      openBtn.click();
      return true;
    }
    return false;
  });

  console.log('OPEN_BTN_CLICKED:' + clicked);
  await sleep(3000);

  // 열린 에디터의 텍스트 가져오기
  const docText = await p.evaluate(() => {
    // 다양한 캔버스 텍스트 셀렉터
    const selectors = [
      '.ProseMirror',
      '[contenteditable="true"]',
      '.writing-block',
      '[data-testid="canvas-document"]',
      'article',
      '.text-base'
    ];
    for (const sel of selectors) {
      const els = Array.from(document.querySelectorAll(sel));
      for (const el of els) {
        if (el.innerText.includes('CHA-FICIAL DIRECTIVE 045-B')) {
          return { found: true, selector: sel, text: el.innerText };
        }
      }
    }
    return { found: false, body: document.body.innerText.slice(-6000) };
  });

  console.log('DOC_FOUND:' + docText.found);
  if (docText.found) {
    console.log('CANVAS_FULL_START');
    console.log(docText.text);
    console.log('CANVAS_FULL_END');
  } else {
    console.log('CANVAS_BODY_TAIL:');
    console.log(docText.body);
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
if 'CANVAS_FULL_START\n' in full and '\nCANVAS_FULL_END' in full:
    content = full.split('CANVAS_FULL_START\n')[1].split('\nCANVAS_FULL_END')[0]
    with open("directive_045b_complete.txt", "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[+] 성공: directive_045b_complete.txt 저장 완료 ({len(content)}자)")
else:
    with open("directive_045b_complete.txt", "w", encoding="utf-8") as f:
        f.write(full)
    print("[-] 전체 덤프 저장 완료")
