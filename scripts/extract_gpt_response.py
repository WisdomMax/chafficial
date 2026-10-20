"""Aside CLI 기반 ChatGPT 최신 응답 자동 추출 스크립트."""

import json
import subprocess
import sys


def extract_response(target_room_url: str, save_path: str = "latest_gpt_response.txt") -> str:
    js_code = f"""
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

  // 스크롤 맨 아래로 이동
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await sleep(1500);

  // 최신 Assistant 메시지 추출
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

  console.log('EXTRACTED:' + JSON.stringify(res));
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
        if line.startswith("EXTRACTED:"):
            data = json.loads(line[len("EXTRACTED:"):])
            text = data.get("text", "")
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"[+] 최신 응답 저장 완료 ({len(text)}자): {save_path}")
            return text
    print("[-] 응답 추출 라인을 찾지 못함. 표준 출력:")
    print(res.stdout)
    if res.stderr:
        print("[-] 표준 에러:", res.stderr)
    return ""


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python extract_gpt_response.py <ChatGPT대화방URL> [저장경로]")
        sys.exit(1)
    room_url = sys.argv[1]
    save_path = sys.argv[2] if len(sys.argv) > 2 else "latest_gpt_response.txt"
    extract_response(room_url, save_path)
