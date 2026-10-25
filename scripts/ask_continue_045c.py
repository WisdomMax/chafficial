import subprocess
import json

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
TARGET_ROOM_URL = "https://chatgpt.com/c/6ad7be96-e470-83e8-a5bf-1e8560f936e3"

message = "DIRECTIVE 045-C (FIRST LIVE REMOTE DEMO DEPLOYMENT) 작성이 중간에 멈췄습니다. 지침 전문을 이어서 완성해 주세요."

js_code = """
const fullText = """ + json.dumps(message) + """;

async function run() {
  const tabs = await listBrowserTabs();
  const gptTab = tabs.find(t => t.url && t.url.includes('6ad7be96-e470-83e8-a5bf-1e8560f936e3'));
  const p = await attachBrowserTab(gptTab.targetId);

  // 1. 입력창 포커스 및 텍스트 삽입
  await p.evaluate((text) => {
    const pms = Array.from(document.querySelectorAll('div.ProseMirror'));
    const el = pms.length > 0 ? pms[pms.length - 1] : document.querySelector('#prompt-textarea');
    if (el) {
      el.focus();
      document.execCommand('selectAll', false, null);
      document.execCommand('insertText', false, text);
    }
  }, fullText);

  await sleep(1500);

  // 2. 전송 버튼 클릭
  const sendRes = await p.evaluate(() => {
    const sendBtn = document.querySelector('button[data-testid="send-button"]') ||
                    document.querySelector('button[aria-label*="보내기"]') ||
                    document.querySelector('button[aria-label*="Send"]');
    if (sendBtn && !sendBtn.disabled) {
      sendBtn.click();
      return { clicked: true };
    }
    return { clicked: false };
  });

  if (!sendRes.clicked) {
    await p.keyboard.press('Enter');
  }

  console.log('SENT:' + JSON.stringify(sendRes));
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
