import subprocess

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"

js_code = """
async function run() {
  const tabs = await listBrowserTabs();
  const gptTab = tabs.find(t => t.url && t.url.includes('6ad7be96-e470-83e8-a5bf-1e8560f936e3'));
  const p = await attachBrowserTab(gptTab.targetId);

  const full = await p.evaluate(() => {
    // 캔버스 에디터 요소 찾기
    const editor = document.querySelector('.ProseMirror') || document.querySelector('[contenteditable="true"]');
    if (editor) {
      editor.scrollTop = editor.scrollHeight;
      return editor.innerText;
    }
    return "";
  });

  console.log('SCROLLED_LEN:' + full.length);
  console.log('---START---');
  console.log(full.slice(-1500));
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

for line in res.stdout.splitlines():
    print(line)
