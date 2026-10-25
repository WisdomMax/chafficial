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

  // 최대 60초간 대기 (3초 간격)
  for (let i = 0; i < 20; i++) {
    await sleep(3000);
    const isBusy = await p.evaluate(() => {
      const stopBtn = document.querySelector('button[data-testid="stop-button"]') ||
                      document.querySelector('button[aria-label*="중지"]') ||
                      document.querySelector('button[aria-label*="Stop"]');
      return !!stopBtn;
    });

    console.log("BUSY_STEP_" + i + ":" + isBusy);
    if (!isBusy && i >= 1) {
      console.log("OUTPUT_COMPLETED!");
      break;
    }
  }

  await sleep(2000);
  await p.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await sleep(1500);

  // 최신 응답 텍스트 추출
  const res = await p.evaluate(() => {
    // 혹시 새 Canvas가 열렸는지 확인
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

  console.log("FINAL_AUDIT_RES:" + JSON.stringify(res));
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
    if line.startswith("FINAL_AUDIT_RES:"):
        data = json.loads(line[len("FINAL_AUDIT_RES:"):])
        text = data.get("text", "")
        with open("directive_045c_received.txt", "w", encoding="utf-8") as f:
            f.write(text)
        print(f"[+] 성공: {data.get('type')}로부터 {len(text)}자 추출 완료 -> directive_045c_received.txt")
        break
    else:
        print(line)
