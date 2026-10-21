"""Aside CLI를 통해 ChatGPT 단일 세션에서 열기, 메시지 전송, 응답 대기 및 추출을 한 번에 수행하는 통합 스크립트."""

import json
import subprocess
import sys


def run_chatgpt_roundtrip(report_path: str, target_room_url: str, save_path: str = "latest_gpt_response.txt"):
    with open(report_path, "r", encoding="utf-8") as f:
        report_text = f.read()

    full_message = f"{report_text}\n\n---\n**제미나이(안티그래비티)에게 지시하세요**"
    print(f"[*] 총 {len(full_message)}자 메시지 전송 및 답변 수신 시작...")

    js_code = f"""
const fullText = {json.dumps(full_message)};
const targetUrl = {json.dumps(target_room_url)};

async function run() {{
  // 1. ChatGPT 탭 열기
  await openTab(targetUrl);
  await sleep(6000);

  // 2. 혹시 '다시 시도' 버튼 등이 있으면 클릭
  await page.evaluate(() => {{
    const retryBtn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('다시 시도') || b.innerText.includes('Retry'));
    if (retryBtn) retryBtn.click();
  }});
  await sleep(2000);

  // 3. 하단 입력창(ProseMirror) 포커스
  await page.evaluate(() => {{
    const all = document.querySelectorAll('div.ProseMirror');
    const target = all[all.length - 1];
    if (target) {{
      target.focus();
      target.click();
    }}
  }});
  await sleep(1000);

  // 4. 키보드로 텍스트 주입
  await page.keyboard.insertText(fullText);
  await sleep(2500);

  // 5. 전송 버튼 클릭 (또는 Enter)
  const clickRes = await page.evaluate(() => {{
    const sendBtn = document.querySelector('button[data-testid="send-button"]') ||
                    document.querySelector('button[data-testid="fruitjuice-send-button"]') ||
                    document.querySelector('button[aria-label*="보내기"]') ||
                    document.querySelector('button[aria-label*="Send"]');
    if (sendBtn && !sendBtn.disabled) {{
      sendBtn.click();
      return {{ success: true }};
    }}
    return {{ success: false }};
  }});

  if (!clickRes.success) {{
    await page.keyboard.press('Enter');
  }}
  console.log("SENT_CLICKED");

  // 6. 생성 시작 및 완료 대기
  console.log("WAITING_FOR_GENERATION...");
  await sleep(4000);

  for (let i = 0; i < 90; i++) {{
    await sleep(2000);
    const isBusy = await page.evaluate(() => {{
      const stopBtn = document.querySelector('button[data-testid="stop-button"]') ||
                      document.querySelector('button[aria-label*="중지"]') ||
                      document.querySelector('button[aria-label*="중단"]') ||
                      document.querySelector('button[aria-label*="Stop"]');
      if (stopBtn) return true;

      const bodyText = document.body.innerText;
      if (bodyText.includes("작업 중입니다") || bodyText.includes("생각 중")) {{
        return true;
      }}
      return false;
    }});

    if (!isBusy && i >= 3) {{
      console.log("GENERATION_FINISHED_AT_STEP:" + i);
      break;
    }}
  }}

  // 7. 안정화 대기
  await sleep(4000);
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await sleep(2000);

  // 8. 최신 Assistant 응답 추출
  const res = await page.evaluate(() => {{
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
        ["/Users/wisdom/.local/bin/aside", "--profile", "c759b216-69cc-436b-941a-dab4e621632d", "repl", js_code],
        check=False,
        capture_output=True,
        text=True,
    )

    extracted_text = ""
    for line in res.stdout.splitlines():
        if line.startswith("FINAL_RESPONSE:"):
            data = json.loads(line[len("FINAL_RESPONSE:"):])
            extracted_text = data.get("text", "")
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(extracted_text)
            print(f"[+] 성공: 최신 응답 저장 완료 ({len(extracted_text)}자) -> {save_path}")
            return extracted_text

    print("[-] 응답 추출 실패. 표준 출력:")
    print(res.stdout)
    if res.stderr:
        print("[-] 표준 에러:", res.stderr)
    return ""


if __name__ == "__main__":
    report = sys.argv[1] if len(sys.argv) > 1 else "reports/DIRECTIVE_005_AUTONOMOUS_HANDOFF_REPORT.md"
    url = sys.argv[2] if len(sys.argv) > 2 else "https://chatgpt.com/c/6ad7be96-e470-83e8-a5bf-1e8560f936e3"
    run_chatgpt_roundtrip(report, url)
