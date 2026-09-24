# -*- coding: utf-8 -*-
"""
Pasada VISUAL de QA: maneja un Chrome real (sin ventana) como lo haria una
persona y guarda capturas PNG.

A diferencia de fijar valores por JavaScript, aca:
  * los clics son eventos de MOUSE reales sobre las coordenadas del elemento
    (si esta tapado, fuera de pantalla o deshabilitado, se nota);
  * se escribe con eventos de teclado;
  * los archivos se suben por el selector real (`DOM.setFileInputFiles`);
  * la ventana tiene tamanio de escritorio (1440x900 por defecto).

Uso desde Python:

    from capturas_web import Navegador
    with Navegador(salida='capturas') as nav:
        nav.ir('http://localhost:8000/web_configurator/')
        nav.clic('[data-tab="estrategias"]')
        nav.captura('estrategias', '#tab-estrategias')

Requiere Chrome instalado y el paquete `websockets` (viene con uvicorn).
Solo ASCII en los mensajes (Ley #4).
"""
import asyncio
import base64
import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request

import websockets

CHROME = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
          r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"]


def _puerto_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Navegador:
    def __init__(self, salida="capturas", ancho=1440, alto=900):
        self.salida = salida
        self.ancho, self.alto = ancho, alto
        os.makedirs(salida, exist_ok=True)
        self._loop = asyncio.new_event_loop()
        self._id = 0
        self.archivos = []

    # ------------------------------------------------------------ ciclo de vida
    def __enter__(self):
        exe = next((c for c in CHROME if os.path.exists(c)), None)
        if exe is None:
            raise RuntimeError("[ERROR] no se encontro Chrome ni Edge")
        self._perfil = tempfile.mkdtemp(prefix="qa_chrome_")
        self._puerto = _puerto_libre()
        self._proc = subprocess.Popen(
            [exe, "--headless=new", "--remote-debugging-port=%d" % self._puerto,
             "--user-data-dir=%s" % self._perfil, "--window-size=%d,%d" % (self.ancho, self.alto),
             "--hide-scrollbars", "--no-first-run", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                with urllib.request.urlopen("http://127.0.0.1:%d/json" % self._puerto) as r:
                    paginas = [p for p in json.load(r) if p.get("type") == "page"]
                if paginas:
                    break
            except OSError:
                pass
            time.sleep(0.1)
        self._ws = self._loop.run_until_complete(
            websockets.connect(paginas[0]["webSocketDebuggerUrl"], max_size=2 ** 26))
        for m in ("Page.enable", "Runtime.enable", "DOM.enable"):
            self._cmd(m)
        self._cmd("Emulation.setDeviceMetricsOverride",
                  width=self.ancho, height=self.alto, deviceScaleFactor=1, mobile=False)
        return self

    def __exit__(self, *exc):
        try:
            self._loop.run_until_complete(self._ws.close())
        finally:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
            shutil.rmtree(self._perfil, ignore_errors=True)
            self._loop.close()

    # ------------------------------------------------------------ protocolo
    def _cmd(self, metodo, **params):
        self._id += 1
        mi_id = self._id

        async def _enviar():
            await self._ws.send(json.dumps({"id": mi_id, "method": metodo, "params": params}))
            while True:
                msg = json.loads(await self._ws.recv())
                if msg.get("id") == mi_id:
                    if "error" in msg:
                        raise RuntimeError("[ERROR] %s: %s" % (metodo, msg["error"]))
                    return msg.get("result", {})
        return self._loop.run_until_complete(_enviar())

    def js(self, expresion):
        r = self._cmd("Runtime.evaluate", expression=expresion, returnByValue=True,
                      awaitPromise=True)
        if "exceptionDetails" in r:
            raise RuntimeError("[ERROR] JS: %s" % r["exceptionDetails"].get("text"))
        return r.get("result", {}).get("value")

    # ------------------------------------------------------------ acciones
    def ir(self, url, espera=2.5):
        self._cmd("Page.navigate", url=url)
        time.sleep(espera)

    def esperar(self, segundos):
        time.sleep(segundos)

    def _centro(self, selector):
        caja = self.js(
            "(() => { const e = document.querySelector(%s); if (!e) return null;"
            " e.scrollIntoView({block: 'center'}); const r = e.getBoundingClientRect();"
            " return {x: r.left + r.width / 2, y: r.top + r.height / 2, w: r.width, h: r.height}; })()"
            % json.dumps(selector))
        if not caja:
            raise RuntimeError("[ERROR] no existe el elemento %s" % selector)
        if caja["w"] == 0 or caja["h"] == 0:
            raise RuntimeError("[ERROR] el elemento %s no se ve (tamanio 0)" % selector)
        time.sleep(0.2)
        return caja

    def clic(self, selector, espera=0.6):
        """Clic de mouse real en el centro del elemento. Falla si otro
        elemento lo tapa (una persona tampoco podria hacer clic)."""
        c = self._centro(selector)
        arriba = self.js(
            "(() => { const t = document.elementFromPoint(%f, %f); const e = document.querySelector(%s);"
            " return !!t && (t === e || e.contains(t) || t.contains(e) || (t.control === e)"
            " || (t.closest && t.closest('label') && t.closest('label').contains(e))); })()"
            % (c["x"], c["y"], json.dumps(selector)))
        if not arriba:
            raise RuntimeError("[ERROR] el elemento %s esta tapado por otro" % selector)
        for tipo in ("mouseMoved", "mousePressed", "mouseReleased"):
            self._cmd("Input.dispatchMouseEvent", type=tipo, x=c["x"], y=c["y"],
                      button="left", clickCount=1)
        time.sleep(espera)

    def escribir(self, selector, texto):
        """Clic en el campo, selecciona todo y escribe (eventos de teclado)."""
        self.clic(selector, espera=0.1)
        self._cmd("Input.dispatchKeyEvent", type="keyDown", key="a", code="KeyA",
                  modifiers=2, windowsVirtualKeyCode=65)
        self._cmd("Input.dispatchKeyEvent", type="keyUp", key="a", code="KeyA",
                  modifiers=2, windowsVirtualKeyCode=65)
        self._cmd("Input.insertText", text=str(texto))
        self.js("document.querySelector(%s).dispatchEvent(new Event('change', {bubbles: true}))"
                % json.dumps(selector))
        time.sleep(0.3)

    def elegir(self, selector, valor):
        """Un <select> nativo no se puede abrir en modo sin ventana: se enfoca
        con clic real y se cambia el valor con los eventos de siempre."""
        self.clic(selector, espera=0.1)
        self._cmd("Input.dispatchKeyEvent", type="keyDown", key="Escape", code="Escape",
                  windowsVirtualKeyCode=27)
        self.js("(() => { const e = document.querySelector(%s); e.value = %s;"
                " e.dispatchEvent(new Event('change', {bubbles: true})); })()"
                % (json.dumps(selector), json.dumps(valor)))
        time.sleep(0.4)

    def archivo(self, selector, ruta, espera=3.0):
        """Sube un archivo del disco por el <input type=file> real."""
        doc = self._cmd("DOM.getDocument")
        nodo = self._cmd("DOM.querySelector", nodeId=doc["root"]["nodeId"], selector=selector)
        self._cmd("DOM.setFileInputFiles", files=[os.path.abspath(ruta)], nodeId=nodo["nodeId"])
        time.sleep(espera)

    def captura(self, nombre, selector=None, margen=12):
        """PNG de toda la ventana o del recuadro de un elemento."""
        params = {"format": "png"}
        if selector:
            self._centro(selector)
            caja = self.js(
                "(() => { const r = document.querySelector(%s).getBoundingClientRect();"
                " return {x: r.left + window.scrollX, y: r.top + window.scrollY, w: r.width, h: r.height}; })()"
                % json.dumps(selector))
            params["clip"] = {"x": max(0, caja["x"] - margen), "y": max(0, caja["y"] - margen),
                              "width": caja["w"] + 2 * margen, "height": caja["h"] + 2 * margen,
                              "scale": 1}
            params["captureBeyondViewport"] = True
        datos = self._cmd("Page.captureScreenshot", **params)["data"]
        ruta = os.path.join(self.salida, nombre + ".png")
        with open(ruta, "wb") as f:
            f.write(base64.b64decode(datos))
        self.archivos.append(ruta)
        print("[OK] captura %s" % ruta)
        return ruta
