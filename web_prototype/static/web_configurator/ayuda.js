/**
 * Ayuda plegable (pedido del Director, 2026-09-24).
 *
 * Los textos explicativos de cada configuracion quedan ocultos y se despliegan
 * con un boton (i) junto a la etiqueta del control o al titulo de la tarjeta.
 * Un boton "Ayuda" en la barra superior muestra u oculta TODA la ayuda de una
 * vez (para quien recien empieza); esa preferencia se recuerda en el navegador.
 *
 * Decisiones de diseno:
 *  - Clic, no "pasar el mouse": el texto largo no desaparece mientras se lee,
 *    funciona en pantallas tactiles y con el teclado.
 *  - Se despliega EN SU LUGAR (no un globo flotante): no se corta en los bordes
 *    ni tapa otros controles.
 *  - Los textos muy cortos (unidades, valores por defecto) siguen a la vista:
 *    son parte de la etiqueta.
 *  - Los avisos, errores y resultados NUNCA se ocultan.
 */
const AyudaPlegable = {
    SELECTOR: '.help-text, .description-text, .tab-intro',
    CORTO: 60,                 // caracteres: por debajo, el texto queda visible
    CLAVE: 'gd_ayuda_visible', // preferencia del boton global (por navegador)
    _n: 0,

    init() {
        this.aplicar(document);
        this._botonGlobal();
    },

    _esAviso(el) {
        const id = (el.id || '') + ' ' + (el.parentElement?.id || '');
        if (/warn|result|error|valid|aviso|stale/i.test(id)) return true;
        if (el.classList.contains('validation-message')) return true;
        return !!(el.getAttribute('style') || '').match(/color\s*:/i);
    },

    _ancla(el) {
        if (el.classList.contains('tab-intro')) return null;         // boton propio en su lugar
        const grupo = el.closest('.form-group');
        const etiqueta = grupo && [...grupo.querySelectorAll('label')].find(l => !el.contains(l));
        if (etiqueta) return etiqueta;
        const tarjeta = el.closest('.card');
        // Dentro del TITULO (no al final del encabezado: correria los botones
        // del encabezado al centro).
        return tarjeta ? (tarjeta.querySelector('.card-header h3')
                          || tarjeta.querySelector('.card-header')) : null;
    },

    aplicar(raiz) {
        const grupos = new Map();   // ancla -> textos
        raiz.querySelectorAll(this.SELECTOR).forEach(el => {
            if (el.dataset.ayuda || this._esAviso(el)) return;
            if (el.textContent.trim().length < this.CORTO) return;
            el.dataset.ayuda = 'si';
            el.id = el.id || ('ayuda-' + (++this._n));
            el.classList.add('ayuda-texto');
            const ancla = this._ancla(el);
            if (!ancla) {
                this._botonEnSuLugar(el);
                return;
            }
            if (!grupos.has(ancla)) grupos.set(ancla, []);
            grupos.get(ancla).push(el);
        });
        grupos.forEach((textos, ancla) => this._botonJunto(ancla, textos));
    },

    _crearBoton(textos, etiqueta) {
        const b = document.createElement('button');
        b.type = 'button';
        b.className = 'ayuda-btn';
        b.setAttribute('aria-expanded', 'false');
        b.setAttribute('aria-controls', textos.map(t => t.id).join(' '));
        b.title = etiqueta || 'Ver ayuda';
        b.setAttribute('aria-label', b.title);
        b.innerHTML = '<span aria-hidden="true">i</span>';
        b.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();   // dentro de un <label> no debe tildar el checkbox
            const abrir = b.getAttribute('aria-expanded') !== 'true';
            b.setAttribute('aria-expanded', String(abrir));
            textos.forEach(t => t.classList.toggle('ayuda-abierta', abrir));
        });
        return b;
    },

    _botonJunto(ancla, textos) {
        ancla.appendChild(this._crearBoton(textos, 'Ver ayuda'));
    },

    _botonEnSuLugar(el) {
        const b = this._crearBoton([el], 'Acerca de esta sección');
        b.classList.add('ayuda-btn-seccion');
        b.innerHTML = '<span class="ayuda-i" aria-hidden="true">i</span> Acerca de esta sección';
        el.parentNode.insertBefore(b, el);
    },

    _botonGlobal() {
        const barra = document.getElementById('btn-import')?.parentElement;
        if (!barra || document.getElementById('btn-ayuda-global')) return;
        const b = document.createElement('button');
        b.id = 'btn-ayuda-global';
        b.type = 'button';
        b.className = 'btn-secondary btn-compactable';
        b.title = 'Mostrar u ocultar todos los textos de ayuda';
        b.innerHTML = '<span class="icon">?</span><span class="btn-label">Ayuda</span>';
        const pintar = (on) => {
            document.body.classList.toggle('ayuda-todo-visible', on);
            b.classList.toggle('activo', on);
            b.setAttribute('aria-pressed', String(on));
        };
        let on = false;
        try { on = localStorage.getItem(this.CLAVE) === '1'; } catch (e) { /* sin storage */ }
        pintar(on);
        b.addEventListener('click', () => {
            on = !on;
            pintar(on);
            try { localStorage.setItem(this.CLAVE, on ? '1' : '0'); } catch (e) { /* sin storage */ }
        });
        barra.insertBefore(b, document.getElementById('btn-import'));
    }
};

document.addEventListener('DOMContentLoaded', () => AyudaPlegable.init());
