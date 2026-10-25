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

  // 최대 90초간 생성 완료 대기 (CPU 부하 최소화: 3초 주기)
  for (let i = 0; i < 30; i++) {
    await sleep(3000);
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

    console.log("WAIT_STEP_" + i + "_IS_BUSY:" + isBusy);
    if (!isBusy && i >= 3) {
      console.log("GENERATION_FINISHED_AT_STEP:" + i);
      break;
    }
  }

  // 완료 후 3초 대기 및 최하단 스크롤
  await sleep(3000);
  await p.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await sleep(2000);

  // 어시스턴트 메시지 또는 캔버스 텍스트 추출
  const res = await p.evaluate(() => {
    // 캔버스가 새로 떴는지 확인
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

  console.log("FINAL_RESULT_JSON:" + JSON.stringify(res));
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
    if line.startswith("FINAL_RESULT_JSON:"):
        data = json.loads(line[len("FINAL_RESULT_JSON:"):])
        text = data.get("text", "")
        with open("latest_audit_045b_response.txt", "w", encoding="utf-8") as f:
            f.write(text)
        print(f"[+] 성공: {data.get('type')}로부터 {len(text)}자 추출 완료 -> latest_audit_045b_response.txt")
        break
    else:
        print(line)
