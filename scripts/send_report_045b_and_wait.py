import json
import subprocess
import time

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
REPORT_PATH = "reports/REPORT_045B_FINAL_ACCEPTANCE.md"
TARGET_ROOM_URL = "https://chatgpt.com/c/6ad7be96-e470-83e8-a5bf-1e8560f936e3"

with open(REPORT_PATH, "r", encoding="utf-8") as f:
    report_text = f.read()

full_message = f"""{report_text}

---
**총괄 감독관(ChatGPT)님께:**
DIRECTIVE 045-B에 명시된 9대 요구사항에 대한 실증 및 무결성 검증을 100% PASS로 완수하여 보고서를 공식 제출합니다.
감사 결과 및 후속 지침(또는 최종 판정)을 내려주시기 바랍니다.
"""

print(f"[*] 총 {len(full_message)}자 메시지 전송 준비 완료")

js_code = f"""
const fullText = {json.dumps(full_message)};

async function run() {{
  const tabs = await listBrowserTabs();
  const gptTab = tabs.find(t => t.url && t.url.includes('6ad7be96-e470-83e8-a5bf-1e8560f936e3'));
  if (!gptTab) {{
    console.log('NO_TAB_FOUND');
    return;
  }}
  const p = await attachBrowserTab(gptTab.targetId);

  // 1. 혹시 열려있는 뷰어(Canvas)가 있다면 닫기
  await p.evaluate(() => {{
    const closeBtn = document.querySelector('button[aria-label="뷰어 닫기"]');
    if (closeBtn) closeBtn.click();
  }});
  await sleep(1000);

  // 2. 하단 입력창 찾기 및 포커스
  const injected = await p.evaluate((text) => {{
    const el = document.querySelector('#prompt-textarea') || document.querySelector('div.ProseMirror');
    if (!el) return false;
    el.focus();
    document.execCommand('selectAll', false, null);
    document.execCommand('insertText', false, text);
    return true;
  }}, fullText);

  console.log('INJECTED:' + injected);
  await sleep(1500);

  if (!injected) {{
    await p.evaluate(() => {{
      const el = document.querySelector('#prompt-textarea') || document.querySelector('div.ProseMirror');
      if (el) el.focus();
    }});
    await p.keyboard.insertText(fullText);
    await sleep(2000);
  }}

  // 3. 전송 버튼 클릭
  const sendRes = await p.evaluate(() => {{
    const sendBtn = document.querySelector('button[data-testid="send-button"]') ||
                    document.querySelector('button[data-testid="fruitjuice-send-button"]') ||
                    document.querySelector('button[aria-label*="보내기"]') ||
                    document.querySelector('button[aria-label*="Send"]');
    if (sendBtn && !sendBtn.disabled) {{
      sendBtn.click();
      return {{ clicked: true, method: 'btn' }};
    }}
    return {{ clicked: false }};
  }});

  console.log('SEND_CLICKED:' + JSON.stringify(sendRes));

  if (!sendRes.clicked) {{
    await p.keyboard.press('Enter');
    console.log('ENTER_PRESSED');
  }}

  // 4. 생성 시작 및 완료 대기 (최대 90초)
  console.log('WAITING_FOR_GENERATION...');
  await sleep(5000);

  for (let i = 0; i < 40; i++) {{
    await sleep(2000);
    const isBusy = await p.evaluate(() => {{
      const stopBtn = document.querySelector('button[data-testid="stop-button"]') ||
                      document.querySelector('button[aria-label*="중지"]') ||
                      document.querySelector('button[aria-label*="중단"]') ||
                      document.querySelector('button[aria-label*="Stop"]');
      if (stopBtn) return true;
      const body = document.body.innerText;
      if (body.includes("작업 중입니다") || body.includes("생각 중")) return true;
      return false;
    }});

    if (!isBusy && i >= 4) {{
      console.log('GENERATION_FINISHED_AT_STEP:' + i);
      break;
    }}
  }}

  // 5. 완료 후 스크롤 및 응답 추출
  await sleep(3000);
  await p.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await sleep(2000);

  const res = await p.evaluate(() => {{
    const turns = Array.from(document.querySelectorAll('[data-message-author-role="assistant"]'));
    if (turns.length > 0) {{
      return {{ ok: true, text: turns[turns.length - 1].innerText }};
    }}
    const articles = Array.from(document.querySelectorAll('article'));
    if (articles.length > 0) {{
      return {{ ok: true, text: articles[articles.length - 1].innerText }};
    }}
    return {{ ok: false, text: document.body.innerText.slice(-6000) }};
  }});

  console.log('FINAL_RESPONSE:' + JSON.stringify(res));
}}
await run();
"""

res = subprocess.run(
    ["/Users/wisdom/.local/bin/aside", "--profile", TARGET_PROFILE, "repl", js_code],
    capture_output=True,
    text=True,
    check=False
)

for line in res.stdout.splitlines():
    if line.startswith("FINAL_RESPONSE:"):
        data = json.loads(line[len("FINAL_RESPONSE:"):])
        text = data.get("text", "")
        with open("latest_gpt_response.txt", "w", encoding="utf-8") as f:
            f.write(text)
        print(f"[+] 성공: 최신 감사 응답 저장 완료 ({len(text)}자)")
        break
    else:
        print(line)
