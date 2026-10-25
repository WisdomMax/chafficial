import json
import subprocess
import time

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
REPORT_PATH = "reports/REPORT_045C_REMOTE_DEMO.md"

with open(REPORT_PATH, "r", encoding="utf-8") as f:
    report_text = f.read()

full_message = f"""{report_text}

---
**총괄 감독관(ChatGPT)님께:**
DIRECTIVE 045-C에 명시된 10대 핵심 요구사항(cloudflared 2026.10.3 업그레이드, --allowed-mail 보호 터널 실증, 관리자 비밀번호 32자리 교체, CF-Connecting-IP 스푸핑 방어, 세션 쿠키 Secure 하드닝, 1분 원클릭 런처 구축 등)에 대한 실증 및 9대 테스트를 100% PASS로 완수하여 REPORT 045-C를 공식 제출합니다.
감사 결과 및 최종 판정을 내려주시기 바랍니다.
"""

print(f"[*] 총 {len(full_message)}자 REPORT 045-C 전송 시작...")

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

  // 1. 하단 채팅 입력창 (마지막 ProseMirror) 특정
  const injectRes = await p.evaluate((text) => {{
    const pms = Array.from(document.querySelectorAll('div.ProseMirror'));
    if (pms.length === 0) return {{ ok: false, error: 'NO_PROSEMIRROR' }};
    const el = pms[pms.length - 1];
    el.focus();
    el.innerHTML = '';
    const success = document.execCommand('insertText', false, text);
    return {{ ok: true, success: success, len: el.innerText.length }};
  }}, fullText);

  console.log('INJECT_RES:' + JSON.stringify(injectRes));
  await sleep(1500);

  // 2. 키보드로 전송 (Enter)
  await p.keyboard.press('Enter');
  console.log('ENTER_PRESSED');

  await sleep(3000);
  const sendCheck = await p.evaluate(() => {{
    const stopBtn = document.querySelector('button[data-testid="stop-button"]') ||
                    document.querySelector('button[aria-label*="중지"]') ||
                    document.querySelector('button[aria-label*="Stop"]');
    return {{ isGenerating: !!stopBtn }};
  }});
  console.log('SEND_CHECK:' + JSON.stringify(sendCheck));
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
