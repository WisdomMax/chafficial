import subprocess

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"

js_code = """
async function run() {
  const tabs = await listBrowserTabs();
  const gptTab = tabs.find(t => t.url && t.url.includes('6ad7be96-e470-83e8-a5bf-1e8560f936e3'));
  const p = await attachBrowserTab(gptTab.targetId);

  const res = await p.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const contBtn = btns.find(b => b.innerText.includes('계속') || b.innerText.includes('Continue'));
    if (contBtn) {
      contBtn.click();
      return { clicked: true, text: contBtn.innerText };
    }
    return { clicked: false, allBtns: btns.map(b => b.innerText.trim()).filter(Boolean) };
  });

  console.log('CONT_RES:' + JSON.stringify(res));
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
    if line.startswith("CONT_RES:"):
        print(line)
        break
