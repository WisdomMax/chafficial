#!/usr/bin/env python3
"""ChatGPT 응답 작성이 완전히 끝날 때까지 대기하고 최신 DIRECTIVE 062를 추출하는 스크립트."""

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
    if (!isBusy && i >= 2) {{
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

  // 최신 응답 텍스트 추출
  const text = await p.evaluate(() => {{
    const main = document.querySelector('main');
    return main ? main.innerText : document.body.innerText;
  }});

  console.log("===FULL_OUTPUT_START===");
  console.log(text.slice(-5000));
  console.log("===FULL_OUTPUT_END===");
}}
await run();
"""

print("[*] ChatGPT 응답 완료 대기 및 DIRECTIVE 062 텍스트 추출 시작...")
res = subprocess.run(
    ["/Users/wisdom/.local/bin/aside", "--profile", TARGET_PROFILE, "repl", js_code],
    capture_output=True,
    text=True,
    check=False,
    timeout=300
)

extracted_text = ""
stdout = res.stdout
if "===FULL_OUTPUT_START===" in stdout and "===FULL_OUTPUT_END===" in stdout:
    extracted_text = stdout.split("===FULL_OUTPUT_START===")[1].split("===FULL_OUTPUT_END===")[0].strip()

with open("reports/DIRECTIVE_062_EXTRACTED.md", "w", encoding="utf-8") as f:
    f.write(extracted_text or stdout)

print(f"[*] DIRECTIVE 062 저장 완료 (길이: {len(extracted_text)}자): reports/DIRECTIVE_062_EXTRACTED.md")
