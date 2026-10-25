import subprocess
import json
import sys

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
TARGET_ROOM_URL = "https://chatgpt.com/c/6ade5dae-1c94-83ee-acf8-d6058171a94d"

js_code = """
const targetUrl = """ + json.dumps(TARGET_ROOM_URL) + """;

async function run() {
  const p = await openTab(targetUrl);
  await sleep(4000);

  // Cloudflare 등 로딩 대기
  for (let i = 0; i < 4; i++) {
    const title = await p.title();
    if (!title.includes('잠시만 기다리십시오') && !title.includes('Just a moment')) {
      break;
    }
    await sleep(2000);
  }

  // 생성 중인지 확인
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

  // 스크롤 아래로
  await p.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await sleep(1500);

  const res = await p.evaluate(() => {
    const turns = Array.from(document.querySelectorAll('[data-message-author-role="assistant"]'));
    if (turns.length > 0) {
      return { ok: true, isBusy: false, text: turns[turns.length - 1].innerText };
    }
    const articles = Array.from(document.querySelectorAll('article'));
    if (articles.length > 0) {
      return { ok: true, isBusy: false, text: articles[articles.length - 1].innerText };
    }
    return { ok: false, isBusy: false, text: document.body.innerText.slice(-6000) };
  });
  res.isBusy = isBusy;

  console.log('FINAL_RESPONSE:' + JSON.stringify(res));
}
await run();
"""

res = subprocess.run(
    ["/Users/wisdom/.local/bin/aside", "--profile", TARGET_PROFILE, "repl", js_code],
    capture_output=True,
    text=True,
    check=False
)

extracted_text = ""
is_busy = False
for line in res.stdout.splitlines():
    if line.startswith("FINAL_RESPONSE:"):
        data = json.loads(line[len("FINAL_RESPONSE:"):])
        extracted_text = data.get("text", "")
        is_busy = data.get("isBusy", False)
        with open("latest_gpt_response.txt", "w", encoding="utf-8") as f:
            f.write(extracted_text)
        print(f"[+] 성공: 최신 응답 저장 완료 ({len(extracted_text)}자, busy={is_busy})")
        break

if not extracted_text:
    print("[-] 추출 실패 stdout:", res.stdout[:500])
    print("[-] stderr:", res.stderr[:500])
