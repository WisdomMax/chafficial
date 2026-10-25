import subprocess
import json

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
TARGET_ROOM_URL = "https://chatgpt.com/c/6ad7be96-e470-83e8-a5bf-1e8560f936e3"

js_code = """
const targetUrl = """ + json.dumps(TARGET_ROOM_URL) + """;

async function run() {
  const p = await openTab(targetUrl);
  await sleep(4000);

  // '다시 시도' 버튼 클릭
  const retried = await p.evaluate(() => {
    const btn = Array.from(document.querySelectorAll('button')).find(b => 
      b.innerText.includes('다시 시도') || b.innerText.includes('Retry')
    );
    if (btn) {
      btn.click();
      return true;
    }
    return false;
  });

  console.log('RETRIED_BTN:' + retried);
  await sleep(5000);

  const title = await p.title();
  console.log('RELOADED_TITLE:' + title);
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
