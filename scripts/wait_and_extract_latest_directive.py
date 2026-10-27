#!/usr/bin/env python3
"""ChatGPT 응답 생성 완료 감지 및 최신 지침/질문 전문 자동 추출 스크립트."""

from __future__ import annotations

import json
import subprocess
import sys
import time

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"

js_code = """
async function run() {
  const p = await attachActiveBrowserTab();
  console.log('ACTIVE_URL:' + await p.url());
  console.log('ACTIVE_TITLE:' + await p.title());

  // 생성 완료 대기 (최대 300초 = 5분)
  let complete = false;
  for (let i = 0; i < 60; i++) {
    const isBusy = await p.evaluate(() => {
      // 1. 중지 버튼 여부
      const stopBtn = document.querySelector('button[data-testid="stop-button"]') ||
                      document.querySelector('button[aria-label*="중지"]') ||
                      document.querySelector('button[aria-label*="중단"]') ||
                      document.querySelector('button[aria-label*="Stop"]');
      if (stopBtn) return true;

      // 2. 생각 중 / 작업 중 표시 여부
      const bodyText = document.body.innerText;
      if (bodyText.includes("작업 중입니다") || bodyText.includes("생각 중…") || bodyText.includes("웹 검색 중")) {
        // 단, 마지막 메시지 영역이 아직 진행 중인지 확인
        const resultStreaming = document.querySelector('.result-streaming');
        if (resultStreaming) return true;
      }

      // 3. 음성/텍스트 스트리밍 클래스
      if (document.querySelector('.result-thinking') || document.querySelector('.result-streaming')) {
        return true;
      }

      return false;
    });

    console.log(`[WAIT_LOOP ${i+1}/60] isBusy: ${isBusy}`);
    if (!isBusy) {
      // 안정성을 위해 3초 추가 대기 후 재확인
      await sleep(3000);
      const isBusyAgain = await p.evaluate(() => {
        const stopBtn = document.querySelector('button[data-testid="stop-button"]') ||
                        document.querySelector('button[aria-label*="중지"]') ||
                        document.querySelector('button[aria-label*="Stop"]');
        return !!stopBtn;
      });
      if (!isBusyAgain) {
        complete = true;
        console.log('GENERATION_COMPLETE_CONFIRMED!');
        break;
      }
    }
    await sleep(5000);
  }

  // 완료 후 맨 아래로 스크롤
  await p.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await sleep(2000);

  // 최신 어시스턴트 메시지 추출
  const res = await p.evaluate(() => {
    // 1. Canvas 에디터에 작성된 경우
    const canvasEditor = document.querySelector('[aria-label="작성을 시작하세요"]') ||
                         document.querySelector('[data-testid="canvas-editor"]') ||
                         document.querySelector('.prose[contenteditable="true"]');
    if (canvasEditor && canvasEditor.innerText.trim().length > 100) {
      return { source: 'canvas', text: canvasEditor.innerText.trim() };
    }

    // 2. 어시스턴트 메시지 턴
    const turns = Array.from(document.querySelectorAll('[data-message-author-role="assistant"]'));
    if (turns.length > 0) {
      const lastTurn = turns[turns.length - 1];
      return { source: 'assistant_turn', text: lastTurn.innerText.trim() };
    }

    // 3. 아티클 요소
    const articles = Array.from(document.querySelectorAll('article'));
    if (articles.length > 0) {
      const lastArt = articles[articles.length - 1];
      return { source: 'article', text: lastArt.innerText.trim() };
    }

    return { source: 'body_fallback', text: document.body.innerText.slice(-10000) };
  });

  console.log('EXTRACTED_SOURCE:' + res.source);
  console.log('EXTRACTED_LEN:' + res.text.length);
  console.log('CONTENT_START');
  console.log(res.text);
  console.log('CONTENT_END');
}
await run();
"""

print("[*] aside 활성 브라우저 탭 연결 및 ChatGPT 생성 완료 대기 중...")
proc = subprocess.Popen(
    ["/Users/wisdom/.local/bin/aside", "--profile", TARGET_PROFILE, "repl", js_code],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1,
)

content_lines = []
in_content = False

while True:
    line = proc.stdout.readline()
    if not line and proc.poll() is not None:
        break
    if not line:
        continue
    line_str = line.rstrip("\n")

    if line_str == "CONTENT_START":
        in_content = True
        continue
    elif line_str == "CONTENT_END":
        in_content = False
        continue

    if in_content:
        content_lines.append(line_str)
    else:
        print(line_str)

proc.wait()

if content_lines:
    full_text = "\n".join(content_lines).strip()
    with open("reports/LATEST_CHATGPT_DIRECTIVE.txt", "w", encoding="utf-8") as f:
        f.write(full_text)
    print(f"\n[+] 최신 지침/답변 추출 성공 ({len(full_text)}자) -> reports/LATEST_CHATGPT_DIRECTIVE.txt")
    print("\n" + "=" * 70)
    print(full_text)
    print("=" * 70 + "\n")
else:
    print("[-] 텍스트 추출에 실패했습니다. stderr:")
    print(proc.stderr.read())
