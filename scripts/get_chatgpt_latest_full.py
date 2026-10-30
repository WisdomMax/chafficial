#!/usr/bin/env python3
import json
import subprocess
import time

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
CHATGPT_URL = "https://chatgpt.com/c/6ae25099-daa0-83e8-8efd-08ef73499525?no_universal_links=1"

js_code = f"""
const p = await openTab({json.dumps(CHATGPT_URL)});
await sleep(3000);

// 응답이 끝날 때까지 최대 40초 대기 (중지 버튼이 사라지거나 전송 버튼이 생길 때까지)
for (let i = 0; i < 8; i++) {{
  const isGenerating = await p.evaluate(() => {{
    const stopBtn = document.querySelector('button[aria-label="중지"]') || 
                    document.querySelector('button[data-testid="stop-button"]') ||
                    Array.from(document.querySelectorAll('button')).find(b => b.innerText && b.innerText.includes('중지'));
    return !!stopBtn;
  }});
  if (!isGenerating) break;
  await sleep(5000);
}}

// 최신 텍스트 추출
const data = await p.evaluate(() => {{
  // 대화 컨테이너 내의 텍스트 또는 턴 목록
  const main = document.querySelector('main');
  return main ? main.innerText : document.body.innerText;
}});

console.log('===FULL_PAGE_TEXT_START===');
console.log(data);
console.log('===FULL_PAGE_TEXT_END===');
"""

res = subprocess.run([
    "/Users/wisdom/.local/bin/aside",
    "--profile", TARGET_PROFILE,
    "exec", js_code
], capture_output=True, text=True)

out = res.stdout or ""
with open("reports/CHATGPT_CONVERSATION_SNAPSHOT.txt", "w", encoding="utf-8") as f:
    f.write(out)

if "===FULL_PAGE_TEXT_START===" in out:
    content = out.split("===FULL_PAGE_TEXT_START===")[1].split("===FULL_PAGE_TEXT_END===")[0].strip()
    print("Snapshot saved! Characters:", len(content))
    # 마지막 2000자 출력
    print("\n--- LAST 2000 CHARACTERS ---")
    print(content[-2000:])
else:
    print("Failed to capture snapshot delimiter. Out length:", len(out))
    print(out[:500])
