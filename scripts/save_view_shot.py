import subprocess
import base64

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"

js_code = """
async function run() {
  const tabs = await listBrowserTabs();
  const gptTab = tabs.find(t => t.url && t.url.includes("6ad7be96-e470-83e8-a5bf-1e8560f936e3"));
  const p = await attachBrowserTab(gptTab.targetId);
  const buf = await p.screenshot();
  console.log("BASE64_DATA:" + buf.toString("base64"));
}
await run();
"""

res = subprocess.run(
    ["/Users/wisdom/.local/bin/aside", "--profile", TARGET_PROFILE, "repl", js_code],
    capture_output=True,
    text=True
)

for line in res.stdout.splitlines():
    if line.startswith("BASE64_DATA:"):
        b64 = line[len("BASE64_DATA:"):].strip()
        data = base64.b64decode(b64)
        with open("chatgpt_current_view.png", "wb") as f:
            f.write(data)
        print(f"[+] 성공: chatgpt_current_view.png 저장 ({len(data)} bytes)")
        break
