#!/usr/bin/env python3
"""ChatGPT 응답 작성이 완전히 끝날 때까지 대기하고 최신 DIRECTIVE 057을 추출하는 스크립트."""

import json
import subprocess
import time

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
CHATGPT_URL = "https://chatgpt.com/c/6ade5dae-1c94-83ee-acf8-d6058171a94d"

js_code = f"""
async function run() {{
  const p = await openTab({json.dumps(CHATGPT_URL)});
  
  // 최대 60회 (약 3~4분) 대기
  for (let i = 0; i < 60; i++) {{
    const isBusy = await p.evaluate(() => {{
      const stopBtn = document.querySelector('button[data-testid="stop-button"]') ||
                      document.querySelector('button[aria-label*="중지"]') ||
                      document.querySelector('button[aria-label*="Stop"]');
      const streaming = document.querySelector('.result-streaming');
      return Boolean(stopBtn || streaming);
    }});

    console.log("CHECK_BUSY [" + i + "]: " + isBusy);
    if (!isBusy && i >= 3) {{
      // 생성이 시작된 후 멈췄는지 추가 3초 확인
      await sleep(3000);
      const stillNotBusy = await p.evaluate(() => {{
        const stopBtn = document.querySelector('button[data-testid="stop-button"]') ||
                        document.querySelector('button[aria-label*="중지"]') ||
                        document.querySelector('button[aria-label*="Stop"]');
        return Boolean(stopBtn);
      }});
      if (!stillNotBusy) {{
        break;
      }}
    }}
    await sleep(4000);
  }}

  // 최신 응답 텍스트 추출 (Canvas 에디터 우선, 일반 어시스턴트 메시지 백업)
  const text = await p.evaluate(() => {{
    // 1. Canvas 에디터
    const editors = Array.from(document.querySelectorAll('.writing-block-editor, .editor-jMsqTn, .ProseMirror.writing-block-open-link-mode'));
    if (editors.length > 0 && editors[editors.length - 1].innerText.length > 100) {{
      return editors[editors.length - 1].innerText;
    }}
    // 2. 어시스턴트 메시지 턴
    const msgs = Array.from(document.querySelectorAll('article[data-testid^="conversation-turn-"], div[data-message-author-role="assistant"]'));
    if (msgs.length > 0) {{
      return msgs[msgs.length - 1].innerText;
    }}
    return '';
  }});

  console.log("LEN:" + text.length);
  console.log("===START===");
  console.log(text);
  console.log("===END===");
}}
await run();
"""

print("[*] ChatGPT 응답 완료 대기 및 DIRECTIVE 057 텍스트 추출 시작...")
res = subprocess.run(
    ["/Users/wisdom/.local/bin/aside", "--profile", TARGET_PROFILE, "repl", js_code],
    capture_output=True,
    text=True,
    check=False,
    timeout=300
)

extracted_text = ""
stdout = res.stdout
if "===START===" in stdout and "===END===" in stdout:
    extracted_text = stdout.split("===START===")[1].split("===END===")[0].strip()

with open("reports/DIRECTIVE_058_EXTRACTED.md", "w", encoding="utf-8") as f:
    f.write(extracted_text or stdout)

print(f"[*] DIRECTIVE 058 저장 완료 (길이: {len(extracted_text)}자): reports/DIRECTIVE_058_EXTRACTED.md")
