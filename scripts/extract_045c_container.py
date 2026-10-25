import subprocess

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"

js_code = """
async function run() {
  const tabs = await listBrowserTabs();
  const gptTab = tabs.find(t => t.url && t.url.includes("6ad7be96-e470-83e8-a5bf-1e8560f936e3"));
  const p = await attachBrowserTab(gptTab.targetId);

  const res = await p.evaluate(() => {
    const headings = Array.from(document.querySelectorAll("h1"));
    const targetH1 = headings.find(h => h.innerText.includes("045-C"));
    if (!targetH1) return "TARGET_H1_NOT_FOUND";

    let container = targetH1.closest("article") || targetH1.parentElement;
    if (container) {
      return container.innerText;
    }
    return targetH1.innerText;
  });

  console.log("RES_LEN:" + res.length);
  console.log("---START---");
  console.log(res);
  console.log("---END---");
}
await run();
"""

res = subprocess.run(
    ["/Users/wisdom/.local/bin/aside", "--profile", TARGET_PROFILE, "repl", js_code],
    capture_output=True,
    text=True
)

for line in res.stdout.splitlines():
    print(line)
