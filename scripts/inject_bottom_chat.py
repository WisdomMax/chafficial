import json
import subprocess
import time

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
REPORT_PATH = "reports/REPORT_045B_FINAL_ACCEPTANCE.md"

with open(REPORT_PATH, "r", encoding="utf-8") as f:
    report_text = f.read()

full_message = f"""{report_text}

---
**총괄 감독관(ChatGPT)님께:**
DIRECTIVE 045-B에 명시된 9대 요구사항에 대한 실증 및 무결성 검증을 100% PASS로 완수하여 보고서를 공식 제출합니다.
감사 결과 및 후속 지침(또는 최종 판정)을 내려주시기 바랍니다.
"""

print(f"[*] 총 {len(full_message)}자 메시지 하단 채팅창 전송 준비 완료")

js_code = f"""
const fullText = {json.dumps(full_message)};

async function run() {{
  const tabs = await listBrowserTabs();
  const gptTab = tabs.find(t => t.url && t.url.includes('6ad7be96-e470-83e8-a5bf-1e8560f936e3'));
  const p = await attachBrowserTab(gptTab.targetId);

  // 1. 하단 채팅 입력창 (마지막 ProseMirror) 특정
  const injectRes = await p.evaluate((text) => {{
    const pms = Array.from(document.querySelectorAll('div.ProseMirror'));
    if (pms.length === 0) return {{ ok: false, error: 'NO_PROSEMIRROR' }};
    const el = pms[pms.length - 1];
    el.focus();
    
    // 이전 내용 비우기
    el.innerHTML = '';
    
    // execCommand로 자연스러운 텍스트 삽입 트리거
    const success = document.execCommand('insertText', false, text);
    return {{ ok: true, success: success, len: el.innerText.length }};
  }}, fullText);

  console.log('INJECT_RES:' + JSON.stringify(injectRes));
  await sleep(1500);

  // 2. 키보드로 전송 (Enter)
  await p.keyboard.press('Enter');
  console.log('ENTER_PRESSED');

  // 3. 3초 대기 후 전송 버튼 상태 및 전송 여부 확인
  await sleep(3000);
  const sendCheck = await p.evaluate(() => {{
    const stopBtn = document.querySelector('button[data-testid="stop-button"]') ||
                    document.querySelector('button[aria-label*="중지"]') ||
                    document.querySelector('button[aria-label*="Stop"]');
    const pms = Array.from(document.querySelectorAll('div.ProseMirror'));
    const lastPm = pms[pms.length - 1];
    return {{
      isGenerating: !!stopBtn,
      inputStillHasText: lastPm ? lastPm.innerText.length > 50 : false
    }};
  }});
  console.log('SEND_CHECK:' + JSON.stringify(sendCheck));

  // 만약 아직 텍스트가 남아있으면 전송 버튼 직접 클릭
  if (sendCheck.inputStillHasText && !sendCheck.isGenerating) {{
    console.log('TRYING_SEND_BUTTON_CLICK...');
    await p.evaluate(() => {{
      const sendBtn = document.querySelector('button[data-testid=\"send-button\"]') ||
                      document.querySelector('button[data-testid=\"fruitjuice-send-button\"]') ||
                      document.querySelector('button[aria-label*=\"보내기\"]') ||
                      document.querySelector('button[aria-label*=\"Send\"]');
      if (sendBtn) sendBtn.click();
    }});
  }}
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
    print(line)
