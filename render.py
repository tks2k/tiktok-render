import sys, subprocess, time, asyncio, base64, shutil
from playwright.async_api import async_playwright
html, out, start, count, fps = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
CLOCK = """(() => { let now = 0; const t0 = 1700000000000;
  performance.now = () => now; Date.now = () => t0 + now;
  window.requestAnimationFrame = cb => 0; window.cancelAnimationFrame = () => {};
  window.__setNow = ms => { now = ms; }; })();"""
async def main():
    ff = shutil.which('ffmpeg')
    p = subprocess.Popen([ff, '-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', str(fps), '-c:v', 'mjpeg', '-i', '-',
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', '-r', str(fps), out], stdin=subprocess.PIPE)
    async with async_playwright() as pw:
        b = await pw.chromium.launch(headless=True, args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        pg = await b.new_page(viewport={'width': 540, 'height': 960})
        pg.on('pageerror', lambda e: print('PAGEERROR', e, flush=True))
        await pg.add_init_script(CLOCK)
        await pg.goto('file://' + html, wait_until='load')
        await pg.wait_for_function('typeof THREE !== "undefined" && typeof step === "function" && typeof frame === "function"', timeout=120000)
        await pg.evaluate('() => { try { reset(); } catch(e) {} }')
        # Logik bis zum Startbild durchlaufen (ohne Rendern), damit Szenen-Zustand stimmt
        await pg.evaluate(f'() => {{ for (let j = 0; j < {start}; j++) {{ __setNow(j * 1000 / {fps}); T = j / {fps}; step(); }} }}')
        t = time.time()
        for i in range(start, start + count):
            data = await pg.evaluate(f'() => {{ __setNow({i} * 1000 / {fps}); T = {i} / {fps}; step(); frame(); return document.getElementById("out").toDataURL("image/jpeg", 0.95).split(",")[1]; }}')
            p.stdin.write(base64.b64decode(data))
            if (i - start) % 20 == 0: print('frame', i, f'{(time.time() - t) / (i - start + 1):.2f}s/f', flush=True)
        await b.close()
    p.stdin.close(); p.wait(); print('SEG DONE', out, flush=True)
asyncio.run(main())
