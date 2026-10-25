import subprocess
import json

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
TARGET_ROOM_URL = "https://chatgpt.com/c/6ad7be96-e470-83e8-a5bf-1e8560f936e3"

js_code = """
const targetUrl = """ + json.dumps(TARGET_ROOM_URL) + """;

async function run() {
  const p = await openTab(targetUrl);
  await sleep(3000);

  const canvasData = await p.evaluate(() => {
    // 1. Canvas 또는 글쓰기 에디터 셀렉터 조사
    const editors = Array.from(document.querySelectorAll('.ProseMirror, [contenteditable="true"], .writing-block, .canvas-content, [data-testid="canvas-document"]'));
    const editorTexts = editors.map((e, idx) => ({ idx, text: e.innerText, len: e.innerText.length }));
    
    // 2. 전체 페이지에서 'CHA-FICIAL DIRECTIVE 045-B'가 포함된 가장 깊은 요소 찾기
    let targetEl = null;
    const allEls = Array.from(document.querySelectorAll('*'));
    for (const el of allEls) {
      if (el.children.length === 0 && el.innerText && el.innerText.includes('CHA-FICIAL DIRECTIVE 045-B')) {
        targetEl = el.parentElement;
        break;
      }
    }
    
    let containerText = "";
    if (targetEl) {
      // 상위 컨테이너로 몇 단계 올라가서 전체 문서 확보
      let curr = targetEl;
      for (let i = 0; i < 5; i++) {
        if (curr.parentElement) curr = curr.parentElement;
      }
      containerText = curr.innerText;
    }

    return {
      editorTexts,
      containerText,
      fullBody: document.body.innerText
    };
  });

  console.log('CANVAS_RESULT_START');
  console.log(JSON.stringify(canvasData));
  console.log('CANVAS_RESULT_END');
}
await run();
"""

res = subprocess.run(
    ["/Users/wisdom/.local/bin/aside", "--profile", TARGET_PROFILE, "repl", js_code],
    capture_output=True,
    text=True,
    check=False
)

full_output = res.stdout
if 'CANVAS_RESULT_START\n' in full_output:
    json_str = full_output.split('CANVAS_RESULT_START\n')[1].split('\nCANVAS_RESULT_END')[0]
    data = json.loads(json_str)
    print("에디터 수:", len(data.get("editorTexts", [])))
    for ed in data.get("editorTexts", []):
        print(f"Editor {ed['idx']}: length {ed['len']}")
        if ed['len'] > 500:
            with open("directive_045b_canvas.txt", "w", encoding="utf-8") as f:
                f.write(ed['text'])
            print(f"[+] 에디터 {ed['idx']} 텍스트를 directive_045b_canvas.txt 에 저장 완료 ({ed['len']}자)")

    c_text = data.get("containerText", "")
    if c_text:
        with open("directive_045b_container.txt", "w", encoding="utf-8") as f:
            f.write(c_text)
        print(f"[+] containerText 저장 완료 ({len(c_text)}자)")
