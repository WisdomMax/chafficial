"""Aside CLI 기반 ChatGPT 마크다운 전문 발송 스크립트."""

import json
import subprocess
import sys


def send_report(report_path: str, target_room_url: str) -> bool:
    with open(report_path, "r", encoding="utf-8") as f:
        full_text = f.read()

    print(f"[*] 전송 시작: {len(full_text)}자 로드 완료 (대상: {target_room_url})")

    js_code = f"""
const textContent = {json.dumps(full_text)};
const targetUrl = {json.dumps(target_room_url)};

async function run() {{
  const openTabs = await listBrowserTabs();
  const gptTab = openTabs.find(t => t.url.includes(targetUrl.split('/').pop()));
  if (gptTab) {{
    await attachBrowserTab(gptTab.targetId);
  }} else {{
    await openTab(targetUrl);
  }}
  await sleep(4000);

  // 1. 하단 입력창(ProseMirror) 포커스
  await page.evaluate(() => {{
    const all = document.querySelectorAll('div.ProseMirror');
    const target = all[all.length - 1];
    if (target) {{
      target.focus();
      target.click();
    }}
  }});
  await sleep(800);

  // 2. 키보드로 100% 전문 주입
  await page.keyboard.insertText(textContent);
  await sleep(2000);

  // 3. 보내기 버튼 클릭
  const clickRes = await page.evaluate(() => {{
    const sendBtn = document.querySelector('button[aria-label="보내기"]') || 
                    document.querySelector('button[data-testid="send-button"]') ||
                    document.querySelector('button[aria-label="메시지 전송"]');
    if (sendBtn && !sendBtn.disabled) {{
      sendBtn.click();
      return {{ success: true }};
    }}
    return {{ success: false }};
  }});

  if (!clickRes.success) {{
    await page.keyboard.press('Enter');
  }}

  // 4. 생성 중 상태 감지
  let generating = false;
  for (let i = 0; i < 20; i++) {{
    await sleep(500);
    generating = await page.evaluate(() => {{
      const stopBtn = document.querySelector('button[aria-label="생성 중지"]') ||
                      document.querySelector('button[data-testid="stop-button"]');
      return !!stopBtn;
    }});
    if (generating) break;
  }}

  console.log('SEND_STATUS:' + JSON.stringify({{ isGenerating: generating }}));
}}
await run();
"""

    res = subprocess.run(
        ["/Users/wisdom/.local/bin/aside", "--profile", "c759b216-69cc-436b-941a-dab4e621632d", "repl", js_code],
        check=False,
        capture_output=True,
        text=True,
    )
    for line in res.stdout.splitlines():
        if line.startswith("SEND_STATUS:"):
            status = json.loads(line[len("SEND_STATUS:"):])
            print("[+] 발송 결과:", status)
            return status.get("isGenerating", False)
    print("[-] 발송 상태 라인을 찾지 못함. 표준 출력:")
    print(res.stdout)
    if res.stderr:
        print("[-] 표준 에러:", res.stderr)
    return False


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("사용법: python send_to_chatgpt.py <보고서파일경로> <ChatGPT대화방URL>")
        sys.exit(1)
    file_path = sys.argv[1]
    room_url = sys.argv[2]
    send_report(file_path, room_url)
