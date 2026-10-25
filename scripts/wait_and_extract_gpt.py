import subprocess
import json
import time

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
TARGET_ROOM_URL = "https://chatgpt.com/c/6ad7be96-e470-83e8-a5bf-1e8560f936e3"

js_code = """
const targetUrl = """ + json.dumps(TARGET_ROOM_URL) + """;

async function run() {
  const p = await openTab(targetUrl);
  await sleep(4000);

  // 최대 60초간 생성이 완료될 때까지 대기
  for (let i = 0; i < 30; i++) {
    const isBusy = await p.evaluate(() => {
      const stopBtn = document.querySelector('button[data-testid="stop-button"]') ||
                      document.querySelector('button[aria-label*="중지"]') ||
                      document.querySelector('button[aria-label*="중단"]') ||
                      document.querySelector('button[aria-label*="Stop"]');
      if (stopBtn) return true;
      const body = document.body.innerText;
      if (body.includes("작업 중입니다") || body.includes("생각 중")) return true;
      return false;
    });

    if (!isBusy) {
      console.log('GENERATION_COMPLETED_AT_LOOP:' + i);
      break;
    }
    await sleep(2000);
  }

  await sleep(2000);
  await p.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await sleep(1500);

  const res = await p.evaluate(() => {
    // 다양한 셀렉터 시도
    const turns = Array.from(document.querySelectorAll('[data-message-author-role="assistant"]'));
    if (turns.length > 0) {
      return { ok: true, text: turns[turns.length - 1].innerText };
    }
    const articles = Array.from(document.querySelectorAll('article'));
    if (articles.length > 0) {
      return { ok: true, text: articles[articles.length - 1].innerText };
    }
    const msgs = Array.from(document.querySelectorAll('.agent-turn, .markdown'));
    if (msgs.length > 0) {
      return { ok: true, text: msgs[msgs.length - 1].innerText };
    }
    return { ok: false, text: document.body.innerText.slice(-6000) };
  });

  console.log('EXTRACTED:' + JSON.stringify(res));
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
    if line.startswith("EXTRACTED:"):
        data = json.loads(line[len("EXTRACTED:"):])
        text = data.get("text", "")
        with open("latest_gpt_response.txt", "w", encoding="utf-8") as f:
            f.write(text)
        print(f"[+] 성공: 최신 응답 저장 완료 ({len(text)}자)")
        break
