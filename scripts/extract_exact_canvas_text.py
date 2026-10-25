import subprocess

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"

js_code = """
async function run() {
  const tabs = await listBrowserTabs();
  const gptTab = tabs.find(t => t.url && t.url.includes('6ad7be96-e470-83e8-a5bf-1e8560f936e3'));
  const p = await attachBrowserTab(gptTab.targetId);

  const text = await p.evaluate(() => {
    // 모든 요소를 순회하면서 'CHA-FICIAL DIRECTIVE 045-B'를 포함하는 가장 긴 텍스트를 찾는다
    let longest = "";
    const all = Array.from(document.querySelectorAll('*'));
    for (const el of all) {
      const t = el.innerText || "";
      if (t.includes('CHA-FICIAL DIRECTIVE 045-B') && t.length > longest.length) {
        longest = t;
      }
    }
    return longest;
  });

  console.log('EXACT_LEN:' + text.length);
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
    with open("directive_045b_complete_full.txt", "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[+] 성공: directive_045b_complete_full.txt 저장 완료 ({len(content)}자)")
else:
    print("[-] 실패, stdout:", res.stdout[:300])
