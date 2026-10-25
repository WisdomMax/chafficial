import subprocess
import json

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
TARGET_ROOM_URL = "https://chatgpt.com/c/6ad7be96-e470-83e8-a5bf-1e8560f936e3"

js_code = """
const targetUrl = """ + json.dumps(TARGET_ROOM_URL) + """;

async function run() {
  const p = await openTab(targetUrl);
  await sleep(2000);

  const status = await p.evaluate(() => {
    const continueBtn = Array.from(document.querySelectorAll('button')).find(b => 
      b.innerText.includes('계속') || b.innerText.includes('Continue') || b.innerText.includes('생성 계속')
    );
    const stopBtn = document.querySelector('button[data-testid="stop-button"]') ||
                    document.querySelector('button[aria-label*="중지"]') ||
                    document.querySelector('button[aria-label*="Stop"]');
    
    return {
      continueBtnExists: !!continueBtn,
      continueBtnText: continueBtn ? continueBtn.innerText : null,
      stopBtnExists: !!stopBtn,
      bodyEndsWith: document.body.innerText.slice(-500)
    };
  });

  console.log('STATUS:' + JSON.stringify(status));
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
    if line.startswith("STATUS:"):
        print(line)
        break
