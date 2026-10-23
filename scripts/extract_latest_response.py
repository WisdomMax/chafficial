import json
import subprocess
import sys


def extract_latest(save_path="latest_gpt_response.txt"):
    js_code = """
async function run() {
  const p = await openTab('https://chatgpt.com/c/6ad7be96-e470-83e8-a5bf-1e8560f936e3');
  await sleep(3000);

  // 생성 중인지 확인
  for (let i = 0; i < 30; i++) {
    const isBusy = await p.evaluate(() => {
      const stopBtn = document.querySelector('button[data-testid="stop-button"]') ||
                      document.querySelector('button[aria-label*="중지"]') ||
                      document.querySelector('button[aria-label*="중단"]') ||
                      document.querySelector('button[aria-label*="Stop"]');
      if (stopBtn) return true;
      const bodyText = document.body.innerText;
      if (bodyText.includes("작업 중입니다") || bodyText.includes("생각 중")) return true;
      return false;
    });
    if (!isBusy) break;
    await sleep(2000);
  }

  await sleep(2000);
  await p.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await sleep(1500);

  const res = await p.evaluate(() => {
    const turns = Array.from(document.querySelectorAll('[data-message-author-role="assistant"]'));
    if (turns.length > 0) {
      return { ok: true, text: turns[turns.length - 1].innerText };
    }
    const articles = Array.from(document.querySelectorAll('article'));
    if (articles.length > 0) {
      return { ok: true, text: articles[articles.length - 1].innerText };
    }
    return { ok: false, text: document.body.innerText.slice(-6000) };
  });

  console.log('FINAL_RESPONSE:' + JSON.stringify(res));
}
await run();
"""
    res = subprocess.run(
        ["/Users/wisdom/.local/bin/aside", "repl", js_code],
        check=False,
        capture_output=True,
        text=True,
    )

    for line in res.stdout.splitlines():
        if line.startswith("FINAL_RESPONSE:"):
            data = json.loads(line[len("FINAL_RESPONSE:"):])
            text = data.get("text", "")
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"[+] 성공: 최신 응답 저장 완료 ({len(text)}자) -> {save_path}")
            return text

    print("[-] 응답 추출 실패:")
    print(res.stdout)
    if res.stderr:
        print(res.stderr)
    return ""


if __name__ == "__main__":
    extract_latest()
