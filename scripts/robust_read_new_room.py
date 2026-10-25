import json
import subprocess
import time

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
NEW_ROOM_ID = "6ade5dae-1c94-83ee-acf8-d6058171a94d"

js_code = f"""
async function run() {{
  let page;
  try {{
    page = await attachActiveBrowserTab();
  }} catch (e) {{
    page = await openTab('https://chatgpt.com/c/{NEW_ROOM_ID}');
  }}

  // 1. URL 확인 및 필요시 이동
  const curUrl = await page.url();
  if (!curUrl.includes('{NEW_ROOM_ID}')) {{
    await page.goto('https://chatgpt.com/c/{NEW_ROOM_ID}');
    await sleep(4000);
  }}

  // 2. '다시 시도' 버튼 처리
  for (let attempt = 0; attempt < 3; attempt++) {{
    const hasError = await page.evaluate(() => {{
      const btns = Array.from(document.querySelectorAll('button'));
      const retry = btns.find(b => b.innerText && b.innerText.includes('다시 시도'));
      if (retry) {{
        retry.click();
        return true;
      }}
      return false;
    }});
    if (!hasError) break;
    await sleep(4000);
  }}

  await sleep(3000);
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await sleep(2000);

  // 3. 최신 어시스턴트 응답 추출
  const res = await page.evaluate(() => {{
    const turns = Array.from(document.querySelectorAll('[data-message-author-role="assistant"]'));
    if (turns.length > 0) {{
      return {{ ok: true, text: turns[turns.length - 1].innerText }};
    }}
    const articles = Array.from(document.querySelectorAll('article'));
    if (articles.length > 0) {{
      return {{ ok: true, text: articles[articles.length - 1].innerText }};
    }}
    return {{ ok: true, text: document.body.innerText }};
  }});

  console.log('EXTRACTED_START');
  console.log(res.text);
  console.log('EXTRACTED_END');
}}
await run();
"""

res = subprocess.run(
    ["/Users/wisdom/.local/bin/aside", "--profile", TARGET_PROFILE, "repl", js_code],
    capture_output=True,
    text=True,
    check=False,
)

output_lines = res.stdout.splitlines()
in_extracted = False
extracted_content = []
for line in output_lines:
    if line == "EXTRACTED_START":
        in_extracted = True
        continue
    if line == "EXTRACTED_END":
        in_extracted = False
        continue
    if in_extracted:
        extracted_content.append(line)

full_result = "\n".join(extracted_content)
with open("reports/AUDIT_046D_NEW_ROOM_RESPONSE.txt", "w", encoding="utf-8") as f:
    f.write(full_result)

print(f"[+] 추출 완료: {len(full_result)}자 저장 -> reports/AUDIT_046D_NEW_ROOM_RESPONSE.txt")
