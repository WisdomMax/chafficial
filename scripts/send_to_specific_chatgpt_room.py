import json
import subprocess
import sys
import time

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
TARGET_ROOM_URL = "https://chatgpt.com/c/6ade5dae-1c94-83ee-acf8-d6058171a94d"
REPORT_PATH = "reports/REPORT_046D_VEHICLE_INTELLIGENCE_AND_MASTER.md"

with open(REPORT_PATH, "r", encoding="utf-8") as f:
    report_text = f.read()

full_message = f"{report_text}\n\n---\n**제미나이(안티그래비티)에게 지시하세요**"

js_code = f"""
const fullText = {json.dumps(full_message)};
const targetUrl = {json.dumps(TARGET_ROOM_URL)};

async function run() {{
  const page = await attachActiveBrowserTab();
  await page.goto(targetUrl);
  await sleep(4000);

  const title = await page.title();
  const url = await page.url();
  console.log('TARGET_TITLE:' + title);
  console.log('TARGET_URL:' + url);

  // '다시 시도' 버튼이 있으면 클릭
  await page.evaluate(() => {{
    const retry = Array.from(document.querySelectorAll('button')).find(b => b.innerText && b.innerText.includes('다시 시도'));
    if (retry) retry.click();
  }});
  await sleep(1500);

  // 입력창 찾기 및 포커스
  const injected = await page.evaluate((text) => {{
    const pms = Array.from(document.querySelectorAll('div.ProseMirror'));
    const el = pms.length > 0 ? pms[pms.length - 1] : document.querySelector('#prompt-textarea');
    if (!el) return false;
    el.focus();
    document.execCommand('selectAll', false, null);
    document.execCommand('insertText', false, text);
    return true;
  }}, fullText);

  console.log('INJECTED:' + injected);
  await sleep(1500);

  if (!injected) {{
    const focused = await page.evaluate(() => {{
      const el = document.querySelector('div.ProseMirror') || document.querySelector('#prompt-textarea');
      if (el) {{ el.focus(); return true; }}
      return false;
    }});
    console.log('FOCUSED:' + focused);
    await page.keyboard.insertText(fullText);
    await sleep(2000);
  }}

  // 전송 버튼 클릭
  const sendRes = await page.evaluate(() => {{
    const sendBtn = document.querySelector('button[data-testid="send-button"]') ||
                    document.querySelector('button[data-testid="fruitjuice-send-button"]') ||
                    document.querySelector('button[aria-label*="보내기"]') ||
                    document.querySelector('button[aria-label*="Send"]');
    if (sendBtn && !sendBtn.disabled) {{
      sendBtn.click();
      return {{ clicked: true }};
    }}
    return {{ clicked: false }};
  }});

  console.log('SEND_RES:' + JSON.stringify(sendRes));
  if (!sendRes.clicked) {{
    await page.keyboard.press('Enter');
  }}

  await sleep(3000);
  console.log('SEND_SUCCESS');
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
