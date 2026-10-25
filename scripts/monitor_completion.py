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

  // 최대 90초 대기
  for (let i = 0; i < 30; i++) {
    await sleep(3000);
    const isBusy = await p.evaluate(() => {
      const stopBtn = document.querySelector('button[data-testid="stop-button"]') ||
                      document.querySelector('button[aria-label*="중지"]') ||
                      document.querySelector('button[aria-label*="Stop"]');
      return !!stopBtn;
    });

    console.log("WAIT_MONITOR_" + i + "_IS_BUSY:" + isBusy);
    if (!isBusy && i >= 1) {
      console.log("GENERATION_COMPLETE_DETECTED!");
      break;
    }
  }

  await sleep(3000);
  await p.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await sleep(2000);

  // 전체 DOM에서 최신 어시스턴트 메시지 추출
  const res = await p.evaluate(() => {
    // 혹시 새 Canvas가 열려있거나 열렸는지
    const canvasEditor = document.querySelector('[aria-label="작성을 시작하세요"]');
    if (canvasEditor && canvasEditor.innerText.length > 100) {
      return { source: 'canvas', text: canvasEditor.innerText };
    }

    const turns = Array.from(document.querySelectorAll('[data-message-author-role="assistant"]'));
    if (turns.length > 0) {
      return { source: 'turns', text: turns[turns.length - 1].innerText };
    }

    const articles = Array.from(document.querySelectorAll('article'));
    if (articles.length > 0) {
      return { source: 'article', text: articles[articles.length - 1].innerText };
    }

    return { source: 'body', text: document.body.innerText.slice(-7000) };
  });

  console.log("FETCHED_RESULT:" + JSON.stringify(res));
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
    if line.startswith("FETCHED_RESULT:"):
        data = json.loads(line[len("FETCHED_RESULT:"):])
        text = data.get("text", "")
        with open("latest_gpt_response_045b_audit.txt", "w", encoding="utf-8") as f:
            f.write(text)
        print(f"[+] 성공: {data.get('source')}에서 {len(text)}자 추출 완료 -> latest_gpt_response_045b_audit.txt")
        break
    else:
        print(line)
