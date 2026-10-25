// Score preliminar por similaridade (botão "auto" do dashboard).
// Script clássico (sem type="module"), para funcionar com o dashboard aberto direto do disco (file://).
// Lógica pura, sem DOM: AutoScore.suggest(alvo, pool) -> { i, u, e, neighbors } ou null.
//   alvo: { title, frente, status }
//   pool: tasks já pontuadas [{ id, title, frente, status, i, u, e }] (sem o alvo e sem as de score auto)
// Método: k vizinhos mais próximos (k=5) por
//   sim = 0,80·texto + 0,15·frente + 0,05·status
//   texto = 0,7·cosseno TF-IDF dos títulos + 0,3·Jaccard de trigramas
//   frente = 1 mesma frente · 0,5 mesmo grupo (platforms/*) · 0 outra
// I, U e E são estimados separadamente (média ponderada por sim²) e puxados para a mediana da frente
// quando nenhum vizinho tem texto parecido (texto < 0,35). Validação leave-one-out: node autoscore.js tasks.csv
(function (root) {
	const K = 5;
	const W_TEXT = 0.8, W_FRENTE = 0.15, W_STATUS = 0.05;
	const W_COS = 0.7, W_TRI = 0.3;
	const CONF_TEXT = 0.35;
	const STOP = new Set('de da do das dos e o a os as para p com em no na um uma por que se ao the of and to for in on via'.split(' '));

	const norm = s => (s || '').toLowerCase().normalize('NFD').replace(/\p{M}/gu, '');
	// Palavras sem acento e sem stopwords, cortadas em 6 letras (stemming simples: integração ~ integrar)
	const words = s => norm(s).split(/[^a-z0-9]+/).filter(w => w.length > 1 && !STOP.has(w)).map(w => w.slice(0, 6));
	function trigrams(s) {
		const t = ' ' + norm(s) + ' ';
		const out = new Set();
		for (let i = 0; i + 3 <= t.length; i++) out.add(t.slice(i, i + 3));
		return out;
	}
	const group = f => (f || '').split('/')[0];
	const median = xs => {
		const s = [...xs].sort((a, b) => a - b);
		const m = s.length >> 1;
		return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
	};
	const clamp = x => Math.max(1, Math.min(5, Math.round(x)));

	function suggest(target, pool) {
		pool = (pool || []).filter(t => [t.i, t.u, t.e].every(x => x >= 1 && x <= 5));
		if (!pool.length) return null;
		const df = new Map();
		pool.forEach(t => new Set(words(t.title)).forEach(w => df.set(w, (df.get(w) || 0) + 1)));
		const n = pool.length;
		const vec = title => {
			const v = new Map();
			words(title).forEach(w => v.set(w, (v.get(w) || 0) + Math.log(1 + n / (df.get(w) || 1))));
			return v;
		};
		const cos = (a, b) => {
			let d = 0, na = 0, nb = 0;
			a.forEach((x, k) => { d += x * (b.get(k) || 0); na += x * x; });
			b.forEach(x => { nb += x * x; });
			return na && nb ? d / Math.sqrt(na * nb) : 0;
		};
		const jaccard = (a, b) => {
			let inter = 0;
			a.forEach(x => { if (b.has(x)) inter++; });
			const uni = a.size + b.size - inter;
			return uni ? inter / uni : 0;
		};
		const vx = vec(target.title), tx = trigrams(target.title);
		const ranked = pool.map(t => {
			const text = W_COS * cos(vx, vec(t.title)) + W_TRI * jaccard(tx, trigrams(t.title));
			const frente = t.frente === target.frente ? 1 : group(t.frente) === group(target.frente) ? 0.5 : 0;
			const status = t.status === target.status ? 1 : 0;
			return { t, text, sim: W_TEXT * text + W_FRENTE * frente + W_STATUS * status };
		}).sort((a, b) => b.sim - a.sim);
		const top = ranked.slice(0, K);
		const same = pool.filter(t => t.frente === target.frente);
		const priorPool = same.length ? same : pool;
		const wsum = top.reduce((s, x) => s + x.sim * x.sim, 0);
		const conf = Math.min(1, Math.max(...top.map(x => x.text)) / CONF_TEXT);
		const out = { neighbors: top.slice(0, 3).map(x => x.t.id) };
		['i', 'u', 'e'].forEach(c => {
			const prior = median(priorPool.map(t => t[c]));
			const knn = wsum ? top.reduce((s, x) => s + x.sim * x.sim * x.t[c], 0) / wsum : prior;
			out[c] = clamp(conf * knn + (1 - conf) * prior);
		});
		return out;
	}

	root.AutoScore = { suggest };

	// Node: exporta e, se chamado com um tasks.csv, roda a validação leave-one-out
	if (typeof module !== 'undefined' && module.exports) {
		module.exports = root.AutoScore;
		if (require.main === module && process.argv[2]) {
			const text = require('fs').readFileSync(process.argv[2], 'latin1');
			const rows = [];
			let row = [], field = '', q = false;
			for (let i = 0; i < text.length; i++) {
				const ch = text[i];
				if (q) { if (ch === '"') { if (text[i + 1] === '"') { field += '"'; i++; } else q = false; } else field += ch; }
				else if (ch === '"') q = true;
				else if (ch === ',') { row.push(field); field = ''; }
				else if (ch === '\n' || ch === '\r') { if (ch === '\r' && text[i + 1] === '\n') i++; row.push(field); rows.push(row); row = []; field = ''; }
				else field += ch;
			}
			if (field || row.length) { row.push(field); rows.push(row); }
			const head = rows.shift();
			const col = (r, k) => (r[head.indexOf(k)] || '').trim();
			const tasks = rows.filter(r => !col(r, 'parent') && /^[1-5]$/.test(col(r, 'i')) && /^[1-5]$/.test(col(r, 'u')) && /^[1-5]$/.test(col(r, 'e'))
				&& !/\[auto=/.test(col(r, 'tags')))
				.map(r => ({ id: col(r, 'id'), title: col(r, 'title'), frente: col(r, 'frente'), status: col(r, 'status'), i: +col(r, 'i'), u: +col(r, 'u'), e: +col(r, 'e') }));
			const score = p => 200 * (0.5 * p.i + 0.35 * p.u + 0.15 * (6 - p.e));
			const err = tasks.map(t => Math.abs(score(suggest(t, tasks.filter(x => x !== t))) - score(t))).sort((a, b) => a - b);
			const mean = err.reduce((s, x) => s + x, 0) / err.length;
			console.log(`${tasks.length} tasks · erro médio do score ${mean.toFixed(0)} · mediana ${Math.round(median(err))} · erro <= 100: ${Math.round(100 * err.filter(x => x <= 100).length / err.length)}%`);
		}
	}
})(typeof window !== 'undefined' ? window : globalThis);
