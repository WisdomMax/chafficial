import json
import os
import subprocess
import sys
import time

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
REPORT_PATH = "reports/REPORT_046D_VEHICLE_INTELLIGENCE_AND_MASTER.md"

with open(REPORT_PATH, "r", encoding="utf-8") as f:
    report_text = f.read()

full_message = f"{report_text}\n\n---\n**제미나이(안티그래비티)에게 지시하세요**"

js_code = f"""
const fullText = {json.dumps(full_message)};

async function run() {{
  const page = await attachActiveBrowserTab();
  console.log('ATTACHED_URL:' + await page.url());

  // 1. 입력창 찾기 및 포커스
  const injected = await page.evaluate((text) => {{
    const pms = Array.from(document.querySelectorAll('div.ProseMirror'));
    const el = pms.length > 0 ? pms[pms.length - 1] : document.querySelector('#prompt-textarea');
    if (!el) return false;
    el.focus();
    document.execCommand('selectAll', false, null);
    document.execCommand('insertText', false, text);
    return true;
  }}, fullText);

  console.log('INJECTED_STATUS:' + injected);
  await sleep(1500);

  // 2. 키보드 백업 주입 (필요시)
  if (!injected) {{
    const focused = await page.evaluate(() => {{
      const el = document.querySelector('div.ProseMirror') || document.querySelector('#prompt-textarea');
      if (el) {{
        el.focus();
        return true;
      }}
      return false;
    }});
    console.log('FOCUSED:' + focused);
    await page.keyboard.insertText(fullText);
    await sleep(2000);
  }}

  // 3. 전송 버튼 클릭
  const sendRes = await page.evaluate(() => {{
    const sendBtn = document.querySelector('button[data-testid="send-button"]') ||
                    document.querySelector('button[data-testid="fruitjuice-send-button"]') ||
                    document.querySelector('button[aria-label*="보내기"]') ||
                    document.querySelector('button[aria-label*="Send"]');
    if (sendBtn && !sendBtn.disabled) {{
      sendBtn.click();
      return {{ clicked: true, btn: 'found' }};
    }}
    return {{ clicked: false, btn: Boolean(sendBtn) }};
  }});

  console.log('SEND_BUTTON_CLICKED:' + JSON.stringify(sendRes));
  if (!sendRes.clicked) {{
    console.log('PRESSING_ENTER_FALLBACK');
    await page.keyboard.press('Enter');
  }}

  // 4. 전송 완료 확인 및 생성 대기
  await sleep(4000);
  console.log('WAITING_FOR_GENERATION_START');
}}
await run();
"""

res = subprocess.run(
    ["/Users/wisdom/.local/bin/aside", "--profile", TARGET_PROFILE, "repl", js_code],
    capture_output=True,
    text=True,
    check=False,
)

print(res.stdout)
