import subprocess
import json

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
TARGET_ROOM_URL = "https://chatgpt.com/c/6ad7be96-e470-83e8-a5bf-1e8560f936e3"

js_code = """
const targetUrl = """ + json.dumps(TARGET_ROOM_URL) + """;

async function run() {
  const p = await openTab(targetUrl);
  await sleep(3000);

  const status = await p.evaluate(() => {
    const pms = Array.from(document.querySelectorAll('div.ProseMirror'));
    const lastPm = pms.length > 0 ? pms[pms.length - 1] : null;
    const pmText = lastPm ? lastPm.innerText : "";
    
    const sendBtn = document.querySelector('button[data-testid="send-button"]') ||
                    document.querySelector('button[aria-label*="보내기"]') ||
                    document.querySelector('button[aria-label*="Send"]');
    const stopBtn = document.querySelector('button[data-testid="stop-button"]') ||
                    document.querySelector('button[aria-label*="중지"]') ||
                    document.querySelector('button[aria-label*="Stop"]');
    
    return {
      pmHasText: !!pmText.trim(),
      pmLength: pmText.length,
      sendBtnExists: !!sendBtn,
      sendBtnDisabled: sendBtn ? sendBtn.disabled : null,
      stopBtnExists: !!stopBtn,
    };
  });

  console.log('INPUT_STATUS:' + JSON.stringify(status));
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
    if line.startswith("INPUT_STATUS:"):
        print(line)
        break
