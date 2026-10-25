import subprocess
import json

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
TARGET_ROOM_URL = "https://chatgpt.com/c/6ad7be96-e470-83e8-a5bf-1e8560f936e3"

js_code = """
const targetUrl = """ + json.dumps(TARGET_ROOM_URL) + """;

async function run() {
  const p = await openTab(targetUrl);
  await sleep(2000);
  await p.reload();
  await sleep(8000);

  // 다시 시도 버튼이 있으면 다시 클릭
  for (let i = 0; i < 3; i++) {
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
    if (!retried) break;
    await sleep(4000);
  }

  const text = await p.evaluate(() => document.body.innerText);
  console.log('RELOAD_BODY_LEN:' + text.length);
  const isError = text.includes('이 ChatGPT 대화를 불러올 수 없습니다');
  console.log('IS_ERROR:' + isError);
  if (!isError) {
    const turns = Array.from(document.querySelectorAll('[data-message-author-role="assistant"]'));
    const lastTurn = turns.length > 0 ? turns[turns.length - 1].innerText : text.slice(-6000);
    return { ok: true, text: lastTurn };
  }
  return { ok: false, text: text.slice(-1000) };
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
