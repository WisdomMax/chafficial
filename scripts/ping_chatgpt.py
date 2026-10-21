"""Aside CLI 기반 ChatGPT 단문 메시지 발송 스크립트."""

import json
import subprocess
import sys


def ping_chatgpt(message: str, target_room_url: str):
    print(f"[*] 메시지 발송 시작: {message} -> {target_room_url}")

    js_code = f"""
const textContent = {json.dumps(message)};
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

  // 2. 키보드로 텍스트 주입
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

  await sleep(3000);
  console.log("PING_SENT_COMPLETE");
}}
await run();
"""

    res = subprocess.run(
        ["/Users/wisdom/.local/bin/aside", "--profile", "c759b216-69cc-436b-941a-dab4e621632d", "repl", js_code],
        check=False,
        capture_output=True,
        text=True,
    )
    print(res.stdout)


if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else "제미나이(안티그래비티)에게 지시하세요"
    url = sys.argv[2] if len(sys.argv) > 2 else "https://chatgpt.com/c/6ad7be96-e470-83e8-a5bf-1e8560f936e3"
    ping_chatgpt(msg, url)
