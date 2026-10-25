import subprocess
import json

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
TARGET_ROOM_URL = "https://chatgpt.com/c/6ad7be96-e470-83e8-a5bf-1e8560f936e3"

js_code = """
const targetUrl = """ + json.dumps(TARGET_ROOM_URL) + """;

async function run() {
  const p = await openTab(targetUrl);
  await sleep(2000);

  // 전송 버튼 클릭
  const clickRes = await p.evaluate(() => {
    const sendBtn = document.querySelector('button[data-testid="send-button"]') ||
                    document.querySelector('button[aria-label*="보내기"]') ||
                    document.querySelector('button[aria-label*="Send"]');
    if (sendBtn && !sendBtn.disabled) {
      sendBtn.click();
      return { clicked: true };
    }
    return { clicked: false };
  });

  console.log('CLICK_RES:' + JSON.stringify(clickRes));

  if (!clickRes.clicked) {
    await p.keyboard.press('Enter');
  }

  // 5초 대기 후 생성이 시작되는지 확인
  await sleep(4000);

  // 최대 60초간 완료 대기
  for (let i = 0; i < 30; i++) {
    const isBusy = await p.evaluate(() => {
      const stopBtn = document.querySelector('button[data-testid="stop-button"]') ||
                      document.querySelector('button[aria-label*="중지"]') ||
                      document.querySelector('button[aria-label*="Stop"]');
      if (stopBtn) return true;
      const body = document.body.innerText;
      if (body.includes("작업 중입니다") || body.includes("생각 중")) return true;
      return false;
    });

    if (!isBusy && i >= 3) {
      console.log('DONE_AT_STEP:' + i);
      break;
    }
    await sleep(2000);
  }

  await sleep(2000);
  await p.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await sleep(1500);

  const res = await p.evaluate(() => {
    const body = document.body.innerText;
    return { text: body.slice(-6000) };
  });

  console.log('RESULT_LEN:' + res.text.length);
  return res.text;
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
