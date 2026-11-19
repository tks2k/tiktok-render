import sys, asyncio, base64
from playwright.async_api import async_playwright
html, outdir, times = sys.argv[1], sys.argv[2], [float(x) for x in sys.argv[3].split(',')]
CLOCK = """(() => { let now = 0; const t0 = 1700000000000;
  performance.now = () => now; Date.now = () => t0 + now;
  window.requestAnimationFrame = cb => 0; window.cancelAnimationFrame = () => {};
  window.__setNow = ms => { now = ms; }; })();"""
HOOK = "window.__R = { go: (t, draw) => { T = t; step(); if (draw) frame(); }, reset: () => reset() };"
src = open(html, encoding='utf-8').read().split('\n'); k = next(i for i, l in enumerate(src) if l.startswith('function reset(){')); src.insert(k + 1, HOOK)
h2 = html.replace('.html', '.prev.html'); open(h2, 'w', encoding='utf-8').write('\n'.join(src))
async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.launch(headless=True, args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        pg = await b.new_page(viewport={'width': 540, 'height': 960})
        pg.on('pageerror', lambda e: print('PAGEERROR', e, flush=True)); pg.on('console', lambda m: print('CONSOLE', m.text, flush=True))
        await pg.add_init_script(CLOCK); await pg.goto('file://' + h2, wait_until='load')
        await pg.wait_for_function('typeof THREE !== "undefined" && !!window.__R', timeout=120000, polling=500)
        await pg.evaluate('() => __R.reset()')
        last = 0
        for n, t in enumerate(times):
            await pg.evaluate(f'() => {{ for (let j = {last}; j < {int(t*30)}; j++) {{ __setNow(j * 1000 / 30); __R.go(j / 30, false); }} }}')
            last = int(t * 30)
            d = await pg.evaluate(f'() => {{ __setNow({t} * 1000); __R.go({t}, true); return document.getElementById("out").toDataURL("image/jpeg", 0.9).split(",")[1]; }}')
            open(f'{outdir}/p{n:02d}.jpg', 'wb').write(base64.b64decode(d)); print('frame', t, flush=True)
        await b.close()
asyncio.run(main())
