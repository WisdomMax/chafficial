import subprocess
import json
import time

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"

js_code = """
async function run() {
  const tabs = await listBrowserTabs();
  const gptTab = tabs.find(t => t.url && t.url.includes("6ad7be96-e470-83e8-a5bf-1e8560f936e3"));
  if (!gptTab) {
    console.log("NO_TAB_FOUND");
    return;
  }
  const p = await attachBrowserTab(gptTab.targetId);

  // 최대 60초간 완료 대기
  for (let i = 0; i < 30; i++) {
    const isBusy = await p.evaluate(() => {
      const stopBtn = document.querySelector('button[data-testid="stop-button"]') ||
                      document.querySelector('button[aria-label*="중지"]') ||
                      document.querySelector('button[aria-label*="중단"]') ||
                      document.querySelector('button[aria-label*="Stop"]');
      if (stopBtn) return true;
      const body = document.body.innerText;
      if (body.includes("작업 중입니다") || body.includes("생각 중") || body.includes("생각하고 있습니다")) return true;
      return false;
    });

    if (!isBusy && i >= 3) {
      console.log("GENERATION_FINISHED_AT_STEP:" + i);
      break;
    }
    await sleep(2000);
  }

  await sleep(3000);
  await p.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await sleep(1500);

  const res = await p.evaluate(() => {
    // 캔버스 또는 일반 메시지 텍스트
    const editor = document.querySelector('[aria-label="작성을 시작하세요"]');
    if (editor && editor.innerText.length > 50) {
      return { type: 'canvas', text: editor.innerText };
    }
    const turns = Array.from(document.querySelectorAll('[data-message-author-role="assistant"]'));
    if (turns.length > 0) {
      return { type: 'chat_turn', text: turns[turns.length - 1].innerText };
    }
    return { type: 'body_tail', text: document.body.innerText.slice(-7000) };
  });

  console.log("FINAL_RESULT:" + JSON.stringify(res));
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
    if line.startswith("FINAL_RESULT:"):
        data = json.loads(line[len("FINAL_RESULT:"):])
        text = data.get("text", "")
        with open("latest_gpt_audit_result.txt", "w", encoding="utf-8") as f:
            f.write(text)
        print(f"[+] 성공: {data.get('type')}에서 {len(text)}자 추출 완료 -> latest_gpt_audit_result.txt")
        break
    else:
        print(line)
