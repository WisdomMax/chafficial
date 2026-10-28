#!/usr/bin/env python3
"""ChatGPT 응답 작성이 완전히 끝날 때까지 대기하고 최신 Canvas 텍스트를 추출하는 스크립트."""

import json
import subprocess
import time

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"

js_code = """
async function run() {
  const p = await attachActiveBrowserTab();
  
  for (let i = 0; i < 20; i++) {
    const isBusy = await p.evaluate(() => {
      const stopBtn = document.querySelector('button[data-testid="stop-button"]') ||
                      document.querySelector('button[aria-label*="중지"]') ||
                      document.querySelector('button[aria-label*="Stop"]');
      const streaming = document.querySelector('.result-streaming');
      return Boolean(stopBtn || streaming);
    });

    console.log("CHECK_BUSY:" + isBusy);
    if (!isBusy) {
      await sleep(3000);
      break;
    }
    await sleep(5000);
  }

  // 최신 에디터 텍스트 추출
  const text = await p.evaluate(() => {
    const editors = Array.from(document.querySelectorAll('.writing-block-editor, .editor-jMsqTn, .ProseMirror.writing-block-open-link-mode'));
    if (editors.length > 0) {
      return editors[editors.length - 1].innerText;
    }
    return '';
  });

  console.log("LEN:" + text.length);
  console.log("===START===");
  console.log(text);
  console.log("===END===");
}
await run();
"""

res = subprocess.run(
    ["/Users/wisdom/.local/bin/aside", "--profile", TARGET_PROFILE, "repl", js_code],
    capture_output=True,
    text=True,
)

with open("reports/DIRECTIVE_055_FINAL.txt", "w", encoding="utf-8") as f:
    f.write(res.stdout)

print("Saved output length:", len(res.stdout))
