# Knowledge Base: formati di dato e istruzione per LLM (XML, Markdown, JSON, YAML, plain text)

**Stato:** documento di lavoro / fondamento di evidenze. Non è l'articolo finito.
**Data di compilazione:** 6 giugno 2026.
**Criterio di selezione delle fonti (questa revisione):** priorità ai test su **modelli attualmente in produzione** (GPT-5.x, Claude Opus/Sonnet/Haiku 4.x, Gemini 2.5 / 3.x). I quattro paper peer-reviewed fondanti su modelli legacy sono mantenuti ma marcati `[LEGACY]` perché sono l'unica base T1 del campo e da lì derivano gran parte delle contraddizioni empiriche. Riferimenti periferici o fuori tema rimossi rispetto alla v1.

---

## 0. Convenzioni

- **Input format** = markup usato nel prompt inviato *al* modello (system + user). **Output format** = markup che il modello è obbligato o invitato a *produrre*. La letteratura confonde di continuo le due cose; qui restano separate, taggate **[Q-IN]** e **[Q-OUT]**.
- **Tier di evidenza:** **T1** peer-reviewed (ACL/EMNLP/ICLR/TACL); **T2** preprint arXiv con metodo solido e codice; **T3** blog tecnico con esperimento riproducibile e N dichiarato; **T4** documentazione vendor (autorevole su *cosa il vendor raccomanda*, non su cosa è empiricamente ottimo); **T5** blog di opinione (solo illustrativo).
- Un risultato è **forte** se ≥2 fonti T1/T2 convergono; **debole** se una sola T2/T3 lo sostiene; **conteso** se T1/T2 si contraddicono; **ignoto** se non esiste studio controllato.
- `[PROD]` segna gli studi che testano modelli oggi in produzione — sono quelli a cui questa revisione dà più peso.

---

## 1. Evidenze scientifiche

### 1.1 Le due domande empiriche distinte

Gran parte delle contraddizioni apparenti svanisce separando due domande:

| Domanda | Operazionalizzazione tipica | Studi di riferimento |
|---|---|---|
| **Q-IN**: cambia l'accuratezza *come strutturo il prompt*? | Stesso contenuto, wrapping variato (plain / MD / XML / JSON / YAML). | He et al. 2024 `[LEGACY]`; Sclar et al. 2024 `[LEGACY]`; ImprovingAgents 2025 `[PROD]`. |
| **Q-OUT**: forzare output strutturato (JSON Schema, XML, YAML) danneggia il ragionamento o la qualità? | Stesso prompt, vincolo di output variato (free-form → istruzione di formato → constrained decoding). | Tam et al. 2024 `[LEGACY]`; "The Format Tax" 2026 `[PROD]`; Checksum 2025 `[PROD]`. |

### 1.2 Studi prioritari — modelli in produzione

#### The Format Tax 2026 — Lee, D'Antoni & Berg-Kirkpatrick `[PROD]` [Q-OUT]
- **ID:** arXiv 2604.03616 (apr 2026). Codice rilasciato. **T2.**
- **Setup:** 6 modelli open-weight + 4 API. Formati: JSON Schema, XML, LaTeX, Markdown vs free-form. Task: MATH-500, GPQA, ZebraLogic, WritingBench. Giudice LLM: gpt-5.4-nano (math), gpt-5.2 (writing).
- **Risultati chiave:**
  - I vincoli di output strutturato degradano sostanzialmente ragionamento e scrittura sui modelli **open-weight**.
  - **Il costo dominante entra a livello di prompt** (istruzione che chiede il formato), non alla maschera di decoding. Il bias di sampling è solo una frazione della perdita.
  - Il **disaccoppiamento** (free-form poi riformatta, o extended thinking) recupera quasi tutta l'accuratezza persa.
  - **I modelli closed-weight di frontiera più recenti (GPT/Claude/Gemini) mostrano un format tax minimo o nullo** — interpretato come gap di training, non come proprietà intrinseca della generazione strutturata.
- **Perché conta:** è lo studio più recente e più direttamente rilevante; smentisce in parte la regola "JSON output danneggia sempre il ragionamento" per i modelli di frontiera attuali.

#### Checksum.ai — "Does Output Format Actually Matter?" `[PROD]` [Q-IN, Q-OUT]
- **Fonte:** checksum.ai/blog, 2 dic 2025. **T3.**
- **Setup:** 30 task × 3 formati (JSON, XML, Markdown) = 90 run. Story writing, coding (LRU cache, BST, trie, topological sort, parser), bug-fix find/replace. Esecuzione: **Claude Haiku 4.5**. Giudice: Claude Sonnet 4.5 con extended thinking. Codice verificato con unit test.
- **Risultati (qualitativi, presentati come bar chart):**
  - Complessivamente Markdown ≈ JSON.
  - **JSON vince a sorpresa la scrittura narrativa** (lo scaffolding strutturato aiuta l'organizzazione del racconto).
  - Tutti i formati simili sul coding.
  - **XML fatica sul find/replace** (non riesce a esprimere pattern di match esatto in modo affidabile in XML).
  - Analisi di similarità same-task: 10/10 bug-fix identici tra formati; 7/10 algoritmi identici (LRU diventa OrderedDict in JSON/MD ma doubly-linked-list in XML); **5/10 testi narrativi solo simili — il formato indirizza la traiettoria creativa.**
- **Debolezze metodologiche:** N=10 per cella; un solo modello esecutore della stessa famiglia del giudice; singolo seed; nessun baseline YAML o plain text; nessun test statistico.

#### ImprovingAgents — "Which Nested Data Format Do LLMs Understand Best?" `[PROD]` [Q-IN]
- **Fonte:** improvingagents.com/blog/best-nested-data-format, 14 ott 2025. **T3.**
- **Setup:** 1.000 domande × formato × modello su config AWS Terraform-like, 6–7 livelli di nesting. Calibrato alla fascia 40–60% di accuratezza. Formati: JSON, YAML, XML, Markdown (heading `#`/`##`/`###` + foglie `key: value`).
- **GPT-5 Nano:** YAML 62,1% [59,1–65,1] > Markdown 54,3% > JSON 50,3% > **XML 44,4%**. Token: MD 38.357 / YAML 42.477 / JSON 57.933 / **XML 68.804** (≈ +79% su Markdown — origine della cifra "80% di token in più").
- **Gemini 2.5 Flash Lite:** YAML 51,9% > MD 48,2% > JSON 43,1% > XML 33,8% (XML −18,1 pp vs YAML).
- **Llama 3.2 3B Instruct:** format-agnostic (49,1–52,7%, nessun ranking significativo).
- **YAML batte XML di 17,7 pp su GPT-5 Nano** — titolo dello studio.
- **Debolezze:** singolo dominio dati; valutazione per substring match; singola codifica Markdown; solo modelli piccoli/economici.

#### ImprovingAgents — TOON benchmarks `[PROD]`
- **Fonte:** improvingagents.com/blog/toon-benchmarks, fine 2025. **T3.**
- Riproduzione indipendente: il vantaggio di accuratezza dichiarato da TOON **non generalizza** ai dati annidati. Sul test nested GPT-5 Nano, **TOON ultimo (43,1%)**. Buono solo per array uniformi di oggetti flat (CSV-like).

#### Chroma "Context Rot" — Hong, Troynikov, Huber 2025 `[PROD]`
- **Fonte:** research.trychroma.com/context-rot, 14 lug 2025. Codice rilasciato. **T2/T3.**
- **Setup:** 18 modelli incl. GPT-4.1, Claude 3.5/3.7/4 Opus/Sonnet, Gemini 2.5 Pro/Flash, Qwen3, Llama-4. NIAH estesa (needle semantici, distrattori), LongMemEval, Repeated-Words.
- **Risultati:** ogni modello degrada in modo monotòno al crescere dell'input, anche a difficoltà costante. Minore similarità semantica needle-domanda → degrado più rapido. **Haystack mescolati (incoerenti) battono quelli coerenti nel retrieval** (la coerenza amplifica il bias posizionale). Claude tende ad astenersi sotto ambiguità; GPT tende ad allucinare con sicurezza.
- **Implicazione per i formati:** i formati verbosi (XML in testa) alzano la lunghezza dell'input e quindi aggravano il context rot, anche se non lo causano direttamente.
- **Conflitto d'interesse:** Chroma vende RAG; metodo comunque solido.

### 1.3 Studi fondanti su modelli legacy (mantenuti, marcati)

#### He et al. 2024 — "Does Prompt Formatting Have Any Impact on LLM Performance?" `[LEGACY]` [Q-IN]
- **ID:** arXiv 2411.10541 (Microsoft), 15 nov 2024. **T2.**
- **Setup:** 4 modelli GPT (GPT-3.5-turbo-0613, GPT-3.5-turbo-16k, GPT-4-32k, GPT-4-1106-preview). Sei task: MMLU, NER-Finance, HumanEval, FIND, CodeXGLUE Java↔C#, HumanEval-X. Formati: plain, Markdown, YAML, JSON. **XML e HTML non testati** — gap riconosciuto dagli autori.
- **Risultati chiave:**
  - La cifra "**42%**" tanto citata è un singolo sotto-dominio MMLU (international law) dove MD→JSON sposta GPT-3.5-turbo-16k di 42 punti. Non è il delta complessivo su MMLU.
  - MMLU complessivo: GPT-3.5-turbo 50,0 (MD) → 59,7 (JSON); **GPT-4-1106 73,9 (JSON) → 81,2 (MD)** — JSON il *peggiore* per GPT-4-1106.
  - HumanEval, GPT-4-32k: **JSON 21,95, plain text 76,2** — JSON collassa (il modello emette chain-of-thought ma mai il codice).
  - **GPT-3.5 tende a preferire JSON; GPT-4 tende a preferire Markdown.** Nessun formato universalmente ottimo.
  - Robustezza cresce con la scala: GPT-4-1106 molto più stabile di GPT-3.5.
- **Limiti:** solo famiglia GPT; niente XML/HTML; modelli closed (meccanismo ignoto); le cifre 42%/200%/300% sono estremi.
- **Rilevanza oggi:** i modelli testati sono fuori produzione, ma è il lavoro che fonda la tesi "nessun formato vince sempre" e l'asimmetria GPT-3.5/GPT-4.

#### Tam et al. 2024 — "Let Me Speak Freely?" `[LEGACY]` [Q-OUT]
- **ID:** arXiv 2408.02442; **EMNLP 2024 Industry**. **T1.**
- **Setup:** GPT-3.5-turbo, GPT-4o, Claude-3-Haiku, Gemini-1.5-Flash, Llama-3-8B, Gemma-2-9B-IT, Mistral-7B. Tre regimi: JSON-mode constrained decoding; istruzioni di formato con schema; two-step NL-poi-converti. Task: GSM8K, Last Letter, Shuffled Objects, DDXPlus, MultiFin, Sports, Task280. 9 varianti di prompt per cella.
- **Risultati chiave:**
  - **Ragionamento:** più stretto il formato → peggiore l'accuratezza. JSON-mode il peggiore per il ragionamento su quasi tutti i modelli. Il two-step NL-to-Format recupera quasi del tutto.
  - **Classificazione:** JSON-mode spesso *pari o meglio* del free-form — la struttura disambigua la selezione della risposta.
  - **Quirk per modello:** **Claude-3-Haiku crolla con JSON ma non con XML** (XML è nativo del training tool-use di Claude); Gemini-1.5-Flash il più consistente; GPT-4o relativamente robusto.
  - Anche con errori di parsing ≈ 0, la qualità del contenuto degrada — è il *vincolo in sé* a danneggiare il ragionamento.
- **Rilevanza oggi:** modelli per lo più superati, ma è la base T1 dell'intera questione Q-OUT. Da leggere insieme a Format Tax 2026, che ne aggiorna le conclusioni sui modelli di frontiera.

#### Sclar et al. 2024 — "Quantifying LMs' Sensitivity to Spurious Features" (FormatSpread) `[LEGACY]` [Q-IN]
- **ID:** arXiv 2310.11324; **ICLR 2024**. **T1.**
- **Setup:** Llama-2 7B/13B/70B + instruction-tuned, Falcon-7B; SuperNaturalInstructions classification; 1-/few-shot. Perturbazioni atomiche (separatori, casing, spaziatura, nomi campo) — più fini degli assi di linguaggio-markup.
- **Risultati:** **fino a 76 punti di spread** tra miglior e peggior template plausibile su un singolo task (Llama-2-13B). La sensibilità persiste con la scala e con l'instruction tuning. Il miglior formato per il modello A spesso non è il migliore per B.
- **Limiti:** prevalentemente classificazione; solo open-weight; non confronta direttamente JSON/XML/Markdown.
- **Rilevanza oggi:** modelli vecchi, ma è la prova canonica della *fragilità ai dettagli di formato*. Va però bilanciata col fatto che i modelli di frontiera attuali sono molto più stabili (He et al.; Format Tax 2026).

#### Liu et al. 2023 — "Lost in the Middle" `[LEGACY]`
- **ID:** arXiv 2307.03172; TACL 12 (2024). **T1.**
- **Risultati:** curva di accuratezza a U nel QA multi-doc a contesto lungo: info a inizio o fine vengono trovate, quelle al centro mancate. Vale anche per modelli long-context espliciti.
- **Rilevanza oggi:** confermata su modelli in produzione dalla replica 18-modelli di Chroma 2025; resta la base per le scelte di posizionamento in contesto lungo.

#### Altri studi tracciati (recenti, su modelli in produzione)

| Studio | ID | Anno | Tier | Contributo |
|---|---|---|---|---|
| Geng et al., JSONSchemaBench | 2501.10868 | 2025 | T2 | Modelli di frontiera ancora falliscono JSON valido su schemi non banali. |
| The Structured Output Benchmark (ExtractBench/StructEval/DeepJSONEval) | 2604.25359 | 2026 | T2 `[PROD]` | Nesting profondo → degrado significativo; ExtractBench: solo 4,6% di pass field-level su 12.867 campi × 35 PDF/schemi. |
| Pinto-Coelho et al. (DSPy+HELM) | 2511.20836 | 2025 | T2 | Structured prompting +6% medio su HELM; ranking cambia su 5/7 benchmark. |
| "Flaw or Artifact?" | 2509.01790 | 2025 | T2 | Buona parte della sensibilità al formato è artefatto di valutazione, non instabilità del modello. |

### 1.4 Economia dei token — numeri concreti

Fonte: ImprovingAgents (stesso contenuto Terraform-like per cella):

| Formato | GPT-5 Nano | Llama 3.2 3B | Gemini 2.5 Flash Lite | Rapporto vs MD |
|---|---|---|---|---|
| Markdown (heading) | 38.357 | 23.692 | 137.708 | **1,00× baseline** |
| YAML | 42.477 | 26.263 | 156.296 | ~1,10–1,13× |
| JSON | 57.933 | 35.808 | 220.892 | ~1,51–1,60× |
| XML | 68.804 | 42.453 | 261.184 | **~1,79–1,90×** |

Meccanica di tokenizzazione (BPE, cl100k / o200k):
- `<tag>` ≈ 2–3 token, `</tag>` ≈ 3–4 (la `/` extra). XML ripete il nome del tag due volte per foglia — fonte dominante dell'~80% di overhead.
- JSON: `"key":` ≈ 3–4 token (virgolette + due punti); `{`, `}`, `,` aggiungono token strutturali.
- YAML: `key:` ≈ 2 token (niente virgolette né chiusura).
- Markdown: `### key` ≈ 3 token.

Prezzi (tariffe flagship mag 2026, indicative):
- GPT-5: $1,25 in / $10 out per M (moltiplicatore output 8×).
- Claude Opus 4.x: $5 in / $25 out per M (5×).
- Gemini 2.5 Pro: $1,25 in / $10 out per M (8×).
- **La scelta del formato di *output* costa 4–8× per token più di quella di input.** Un output XML verboso costa circa il doppio di un output Markdown per gli stessi dati.

Caching:
- **Anthropic prompt caching:** fino a 90% costo / 85% latenza in meno su prefissi cached. Format-agnostico, ma i confini semantici netti di XML offrono breakpoint di cache naturali.
- **OpenAI prompt caching:** automatico, implicito; format-agnostico.
- **Nessuna evidenza pubblica** che un sistema di caching favorisca un markup specifico.

### 1.5 Interazioni con il contesto lungo

- **Lost-in-the-middle è robusto** anche sui modelli di frontiera 2025–2026 (replica 18-modelli Chroma).
- **Nessuno studio controllato pubblicato** incrocia il formato di markup con *più lunghezze di contesto* a contenuto costante. È un buco della letteratura (lo coprirà la Suite 8 del protocollo).
- Evidenza indiretta che il formato pesi di più al crescere dell'input:
  - Lo stress test ImprovingAgents usava input 87–745 KB e lo spread arrivava a 17,7 pp; a input piccoli gli stessi autori riportano ~100% su tutti i formati.
  - Anthropic prescrive di avvolgere ogni documento lungo in `<document><document_content>…</document_content><source>…</source></document>` e di ancorare le risposte con citazioni verbatim.
  - Il risultato Chroma "haystack mescolato batte haystack coerente" implica che scelte di formato che frammentano la coerenza narrativa possano *aiutare* il recall a centro-contesto — il che contrasta con il default Markdown prosa-friendly per input lunghi.

### 1.6 Sicurezza e prompt injection — superficie specifica per formato

- **OWASP LLM Top 10 (2025):** LLM01 Prompt Injection resta #1; LLM05 Improper Output Handling copre gli output LLM non sanitizzati che innescano XSS/SSRF/RCE.
- **L'esfiltrazione via link-immagine Markdown è il vettore dominante nel 2025–2026** (Simon Willison, Johann Rehberger): exploit documentati su ChatGPT, Bard, Writer.com, Amazon Q, NotebookLM, GitHub Copilot Chat, GitLab Duo. L'incidente Superhuman di gen 2026 ha sfruttato una CSP allow-list che includeva `docs.google.com` per esfiltrare via Google Forms.
- **XML vs Markdown per *difendere* dall'injection — conteso:**
  - Anthropic + AWS prescriptive guidance: avvolgere il contenuto non fidato in tag XML; AWS aggiunge **tag con sale** (`<doc-abcde12345>…</doc-abcde12345>`) per battere il tag-spoofing.
  - Lo studio Schneidenbach (480 test: 24 scenari × 5 modelli OpenAI × 2 strategie di delimitatore × 2 posizioni): **differenza pratica minima** tra delimitatori XML e Markdown sui modelli OpenAI. Claude è XML-tuned e ne beneficia probabilmente più di GPT.
- **Il constrained decoding riduce l'injection lato output** (non può emettere `<script>` se lo schema lo vieta) ma **non fa nulla per l'injection lato input**. La tool-mode stretta riduce i bug di argomenti malformati ma non impedisce a un attaccante di pilotare la scelta del tool.

### 1.7 Contraddizioni tra studi (esplicite)

1. **JSON-migliore vs JSON-peggiore.** He et al.: JSON migliore per GPT-3.5 su MMLU/HumanEval; **JSON catastrofico per GPT-4-32k su HumanEval** (21,95 vs 76,2). Tam et al.: JSON-mode peggiore per il ragionamento, migliore per molte classificazioni. ImprovingAgents: JSON a metà classifica sul retrieval annidato. **Risoluzione:** input-format JSON ≠ output-mode JSON; asimmetria ragionamento/classificazione; forte specificità per modello.
2. **XML-raccomandato-dal-vendor vs XML-empiricamente-peggiore.** Anthropic raccomanda fortemente XML per lo scaffolding del prompt; ImprovingAgents e Checksum lo trovano peggiore per retrieval annidato e find-replace. **Risoluzione:** la raccomandazione Anthropic riguarda il **partizionare il prompt** (istruzioni vs contesto vs esempi), non il codificare payload di dati o generare output. Lavori diversi.
3. **La scala risolve la sensibilità, oppure no.** Sclar 2024: persiste con la scala. He et al. 2024: GPT-4-1106 molto più robusto di GPT-3.5. Format Tax 2026: i modelli closed di frontiera mostrano tax "minimo o nullo". **Sintesi attuale:** RLHF e training mirato alla robustezza di formato hanno chiuso gran parte del gap sui modelli proprietari di frontiera; i modelli open-weight piccoli mostrano ancora oscillazioni ampie.
4. **"Lo structured prompting aiuta" vs "lo structured output danneggia."** DSPy+HELM 2025: +6% medio su HELM. Tam 2024: l'output strutturato danneggia il ragionamento. Operazionalizzazioni diverse, sistematicamente confuse nella letteratura divulgativa.
5. **Entità della sensibilità al formato.** Sclar: spread 76 pt. He et al.: spread ≈10–40 pt. "Flaw or Artifact?" 2509.01790: buona parte è artefatto di valutazione.
6. **La pretesa "OpenAI 73% preferenza per prompt strutturati".** Risalente a una sola fonte secondaria. **Nessuna fonte primaria localizzata.** Da trattare come non verificata; non citare senza conferma primaria.

### 1.8 Debolezze metodologiche comuni al campo

1. "Formato" confonde più variabili (sintassi markup, lunghezza, delimitatori, nomi campo).
2. Esperimenti input-format e output-format etichettati con la stessa parola ("JSON").
3. Dominano i modelli proprietari closed; il meccanismo (tokenizer vs distribuzione di training vs RLHF) non è districabile.
4. Le cifre da titolo (42%, 76 punti, 80% token) sono in genere massimi; le tendenze centrali sono più piccole.
5. Ristrettezza dei benchmark — dominano MMLU, GSM8K, HumanEval, SuperNaturalInstructions.
6. Nessun baseline "plain text" standardizzato tra i paper.
7. Formato e brevità confusi insieme.
8. La maggior parte degli studi riporta stime puntuali senza intervalli di confidenza (Tam et al. è un'eccezione).

---

## 2. Linee guida ufficiali dei vendor

### 2.1 Anthropic (famiglia Claude 4.x: Haiku 4.5, Sonnet 4.5/4.6, Opus 4.5–4.8)

**Struttura dell'input** (docs.claude.com/.../prompt-engineering/use-xml-tags):
- "Quando i prompt coinvolgono più componenti come contesto, istruzioni ed esempi, i tag XML possono fare la differenza. Aiutano Claude a fare il parsing più accuratamente."
- Tag come `<instructions>`, `<example>`, `<formatting>` per separare le parti.
- "Non esistono tag XML 'migliori' canonici su cui Claude sia stato addestrato in particolare."
- Nesting `<outer><inner></inner></outer>` per contenuto gerarchico.

Best practice Claude 4.x:
- "Struttura i prompt con tag XML. Avvolgere ogni tipo di contenuto nel suo tag riduce le interpretazioni errate."
- Few-shot: 3–5 esempi, avvolti in `<example>` / `<examples>`.
- Controllo dello stile di output: "rimuovere il markdown dal prompt può ridurre il volume di markdown nell'output."
- Opus 4.8 "interpreta i prompt in modo letterale ed esplicito, in particolare a livelli di effort più bassi."
- **Prefill deprecato per Claude 4.6+** — un turno assistant precompilato restituisce HTTP 400.

Contesto lungo (long-context-tips):
- "Metti i dati lunghi in cima, sopra query, istruzioni ed esempi. Le query alla fine possono migliorare la qualità fino al 30% nei nostri test."
- "Struttura contenuto e metadati con tag XML: `<document><document_content>…</document_content><source>…</source></document>`."
- "Ancora le risposte alle citazioni" per i task su documenti lunghi.

**Structured outputs** (GA 4 feb 2026):
- Due modalità: `output_config.format` (JSON Schema) e tool use con `strict: true`.
- Meccanismo: constrained decoding con grammatica compilata; cache 24h.
- "Il modello letteralmente non può produrre token che violino lo schema."
- Limiti: niente schemi ricorsivi; `additionalProperties: false` obbligatorio; **incompatibile con le citazioni** e con il prefill in JSON output mode.
- Caveat esplicito: "garantisce che l'output aderisca al formato, non che sia accurato al 100%."
- La pagina sulla consistenza ora rimanda agli Structured Outputs nativi **invece dei** workaround XML/prefill — cambio di posizione notevole.

### 2.2 OpenAI (GPT-4.1, GPT-5, GPT-5.1, GPT-5.2; serie reasoning)

**Guida prompting GPT-4.1** (cookbook.openai.com, 14 apr 2025) — primo documento OpenAI a ordinare esplicitamente i formati:
- "1. Markdown: consigliamo di partire da qui, con titoli markdown per sezioni e sottosezioni (gerarchia anche profonda, H4+)."
- "2. XML: funzionano bene anche questi. XML è comodo per avvolgere con precisione una sezione (inizio e fine), aggiungere metadati ai tag, abilitare il nesting."
- "3. JSON è altamente strutturato e ben compreso dal modello, in particolare in contesti di coding. Però è più verboso e richiede l'escape di caratteri."

Per il wrapping di documenti in contesto lungo la guida inverte la preferenza:
- "XML ha funzionato bene nei nostri test di contesto lungo: `<doc id='1' title='The Fox'>…</doc>`."
- "JSON ha reso particolarmente male in questo caso. Esempio: `[{'id': 1, 'title': 'The Fox', 'content': '…'}]`."

Posizionamento istruzioni:
- "Idealmente metti le istruzioni sia all'inizio sia alla fine del contesto fornito: abbiamo trovato che rende meglio rispetto a solo sopra o solo sotto."
- "Se ci sono istruzioni in conflitto, GPT-4.1 tende a seguire quella più vicina alla fine del prompt."

**Guide GPT-5 / 5.1 / 5.2** (ago 2025, nov 2025, dic 2025): introducono blocchi spec in stile XML negli esempi OpenAI stessi (`<context_gathering>`, `<output_verbosity_spec>`, `<tool_usage_rules>`). Convergenza col pattern a tag XML di Anthropic. Parametri `reasoning_effort` (minimal/low/medium/high) e `verbosity`. GPT-5.2: "L'ambiguità ora è un bug."

**Modelli reasoning (o-series / GPT-5):** sopprimono il Markdown in output di default; serve `"Formatting re-enabled"` come prima riga del developer message; non esporre `temperature`, `max_tokens`, `logprobs`. Consigliato: delimitatori chiari (Markdown o XML), evitare prompting CoT pesante (il ragionamento è interno).

**Structured Outputs:**
- Due forme: tool con `strict: true`; `response_format` / `text.format` con `json_schema` `strict: true`.
- "Sui nostri eval di schema JSON complessi, gpt-4o-2024-08-06 con Structured Outputs ottiene un 100% perfetto. gpt-4-0613 sta sotto il 40%."
- Strict richiede `additionalProperties: false`, tutti i campi `required`, niente schemi ricorsivi in strict mode.
- Incompatibilità: non con `parallel_tool_calls: true`.
- "Usate esclusivamente il campo tools per passare i tool, invece di iniettare manualmente le descrizioni nel prompt."

### 2.3 Google Gemini (Gemini 2.5 Pro/Flash/Flash Lite, Gemini 3.x, Gemini Nano)

**Prompt design strategies** (ai.google.dev, agg. 28 apr 2026):
- "Un modo efficace ed efficiente di personalizzare il comportamento è fornire istruzioni chiare e specifiche."
- Consistenza few-shot: "Mantieni un formato coerente in tutti gli esempi, prestando attenzione a tag XML, spazi bianchi, newline e separatori."
- "Mentre puoi specificare il formato di oggetti JSON semplici via prompt, consigliamo la feature di structured output dell'API Gemini per JSON Schema più complessi."

**Gemini 3** (ai.google.dev/gemini-api/docs/gemini-3): "Metti istruzioni o domande specifiche alla fine del prompt, dopo il contesto dati." — **enfasi opposta al 'entrambe le estremità' di OpenAI.** "Di default Gemini 3 è meno verboso."

**Gemini Nano** (developers.google.com/ml-kit/genai/...): guida sui delimitatori più chiara di Google — "Usa delimitatori come `<background_information>`, `<instruction>` e `##` per separare le parti del prompt. Usare `##` tra i componenti è particolarmente critico per Gemini Nano."

**Structured outputs:**
- `response_mime_type: "application/json"` + `response_schema` (sottoinsieme OpenAPI) su ≤2.0; `response_json_schema` (JSON Schema completo) su 2.5+.
- "Lo structured output garantisce JSON sintatticamente corretto, non che i valori siano semanticamente corretti."
- Ordine delle proprietà preservato su 2.5+ via `propertyOrdering`.
- Avviso Vertex AI esplicito: "Usare lo structured output su modelli Gemini tuned può ridurre la qualità del modello."

### 2.4 Microsoft / Azure OpenAI

- Pagina Azure prompt-engineering (volutamente agnostica sul formato): "Sii specifico. Sii descrittivo. A volte devi ripeterti: dai istruzioni prima e dopo il contenuto primario." "L'ordine conta (recency bias)."
- Pagina advanced usa schemi JSON nel system message come pattern di estrazione canonico.
- Structured Outputs: eredita il comportamento OpenAI (stessi requisiti `strict: true`, stesse incompatibilità, stessa pretesa del 100%).

### 2.5 Confronto tra vendor

| Dimensione | Anthropic | OpenAI | Google | Microsoft |
|---|---|---|---|---|
| Markup di default per la struttura del prompt | **Tag XML** (esplicito, primario) | **Markdown** primo, XML secondo, JSON scarso per contesto lungo | XML o Markdown, "la coerenza conta" | Agnostico; affidarsi alla separazione di ruolo |
| Esempi few-shot | `<example>`; 3–5 | sezione `# Examples` Markdown | formato coerente incl. XML | prima o dopo, non interposti |
| Posizionamento in contesto lungo | dati lunghi prima; query alla fine (fino a **+30%**) | istruzioni a **entrambe** le estremità | istruzioni alla **fine**, dopo i dati | prima e dopo il contenuto primario |
| Controllo stile output | "togli Markdown dal prompt per ridurlo nell'output" | blocchi spec stile XML negli esempi (GPT-5+) | meno verboso di default in G3 | n/d |
| Meccanismo structured output | constrained decoding (grammatica compilata, cache 24h) | constrained sampling (schema cached) | constrained decoding | eredita OpenAI |
| Pretesa di affidabilità | "il modello non può produrre token che violano" | "100%" di compliance sugli eval interni | "sintatticamente corretto, non semanticamente" | eredita OpenAI |
| Incompatibilità notevoli | citazioni; prefill (4.6+); schemi ricorsivi | parallel tool calls; ricorsivi in strict | modelli tuned possono degradare; nesting profondo può dare 400 | come OpenAI |
| Svolta 2025–26 | ora indirizza dai workaround XML/prefill agli Structured Outputs nativi | blocchi spec a tag XML ora nei propri esempi | JSON Schema completo su 2.5+; ordine preservato | segue OpenAI |

### 2.6 Linee guida vendor vs evidenza empirica

| Raccomandazione vendor | Stato dell'evidenza | Commento |
|---|---|---|
| Anthropic: "usa tag XML per strutturare i prompt" | **Evidenza diretta debole** specifica per Claude | Tam et al. mostra che Claude-3-Haiku è XML-friendly (nessun crollo JSON-mode), a supporto. Nessun numero A/B pubblico di Anthropic. ImprovingAgents/Checksum mostrano XML *peggiore* per Q&A su dati annidati e find-replace **in output**, ma la raccomandazione riguarda il partizionamento dell'input, non l'output. Coerente **per il suo ambito**. |
| OpenAI GPT-4.1: "Markdown prima" | **Allineata all'evidenza** per la struttura dell'input | He et al.: GPT-4 preferisce Markdown su MMLU. ImprovingAgents: Markdown buon compromesso costo/accuratezza. Coerente. |
| OpenAI: "JSON rende male nei documenti a contesto lungo" | **Allineata** | He et al. GPT-4-32k HumanEval JSON 21,95 vs plain 76,2; ImprovingAgents JSON peggiore di Markdown su tutti e tre i modelli. Coerente. |
| OpenAI: "usa il campo tools, non iniettare descrizioni" | **Allineata** | Tool-mode stretta <0,1% di violazioni; iniezione manuale 5–10% secondo OpenAI. |
| OpenAI 100% di compliance | **Probabilmente sovrastimata** | Solo eval interni; valutazioni esterne (JSONSchemaBench) mostrano fallimenti su schemi non banali. |
| Anthropic "garanzia" via constrained decoding | **Tecnicamente accurata sulla sintassi**, ma Anthropic stessa nega la correttezza semantica | "Garanzia di formato ≠ accuratezza." |
| Anthropic "query alla fine +30%" | **Plausibile**, nessuna replica esterna localizzata | Eval interni; Liu 2023 supporta la U-shape sottostante. |
| Google Gemini 3 "istruzioni alla fine" | **Vendor-specifica; contraddice il 'entrambe le estremità' di OpenAI** | Nessuno studio terzo confronta le due prescrizioni testa a testa. |
| Vendor che raccomandano JSON Schema per l'output | **Allineata sulla compliance, contesa sulla qualità del ragionamento** | Tam 2024 e Format Tax 2026: i modelli open-weight perdono accuratezza sostanziale sotto JSON stretto. I vendor non espongono questo trade-off. |

**Dove i vendor tacciono e l'evidenza parla:**
- Costo di qualità del ragionamento dell'output JSON stretto sui modelli open-weight (Tam, Format Tax).
- Esfiltrazione via link-immagine Markdown come vettore per qualunque modello con superficie di rendering immagini.
- Forte resa di YAML sui dati annidati (nessun vendor lo evidenzia, eppure ImprovingAgents lo dà migliore su 2/3 modelli).
- Gap di costo in token (~80%) di XML su Markdown per gli stessi dati annidati.

---

## 3. Matrice formato × task × modello

Simboli: **★★★** forte (più T1/T2 convergono); **★★** debole (singola T2/T3 o T1 contesa); **★** debole/conteso; **—** nessun dato o fortemente dipendente dal task.

### 3.1 Formato di input (Q-IN)

| Tipo di task | GPT-4.1/5.x | Claude 4.x | Gemini 2.5 / 3 | Llama / open piccoli | Confidenza |
|---|---|---|---|---|---|
| Classificazione single-turn | MD ≈ XML > JSON | XML > MD ≈ JSON | XML ≈ MD > JSON | ~agnostico | ★★ |
| Ragionamento multi-step | MD > XML > JSON | XML > MD; evita JSON pesante | MD ≈ XML; istruzioni alla fine | sensibile al template (Sclar swing 76 pt) | ★★★ sulla sensibilità, ★★ sul ranking |
| Generazione di codice | MD > plain > JSON; XML competitivo | XML competitivo; MD bene | MD o XML | sensibile al formato | ★★ |
| Editing / bug-fix find-replace | MD o JSON (evita XML per i payload FR, Checksum) | MD (Checksum) | — | — | ★★ |
| Scrittura long-form creativa | MD o JSON (sorpresa Checksum: JSON vince) | MD o JSON | MD | — | ★ (conteso; Checksum N=10) |
| Estrazione (NER / campi) | MD con esempi; structured output per il cast finale | tool-use JSON schema; XML per avvolgere la fonte | controlled-gen `response_json_schema` | — | ★★★ |
| Comprensione dati annidati profondi | **YAML o Markdown** > JSON > XML | (non testato su scala; atteso XML competitivo su Claude) | **YAML > MD > JSON > XML** | agnostico su modelli minuscoli | ★★ (GPT-5 Nano, Gemini Flash Lite) |
| QA documenti contesto lungo (>50K) | doc avvolti in XML; quote-first; istruzioni a entrambe le estremità | wrap XML `<document><source>`; query alla fine; quote-first | istruzioni alla fine | non testato | ★★ (vendor + Liu 2023) |
| Passaggio di stato multi-agente | JSON / JSON-RPC dominante (MCP, A2A, ACP, ANP); pseudocodice mostra risparmi di token (CodeAgents) | uguale | uguale | — | ★★ per la convenzione JSON; ★ per l'efficienza pseudocodice |
| Blocchi di contesto RAG | heading MD o XML `<document>`; metadati index/title | `<document><document_content><source>` | blocchi di retrieval strutturati | — | ★★ |

### 3.2 Formato di output (Q-OUT)

| Tipo di task | Output consigliato | Note / evidenza |
|---|---|---|
| Classificazione | **JSON schema strict** (Tam: il vincolo aiuta; OpenAI strict <0,1% violazioni) | ★★★ |
| Estrazione / dati strutturati | **JSON schema strict, tool-mode preferito** | ★★★ (vendor + JSONSchemaBench) |
| Math / ragionamento multi-step | **Prima free-form, poi converti** (two-step NL-to-Format, Tam; Format Tax 2026: il disaccoppiamento recupera la perdita) | ★★★ |
| Scrittura creativa | Free-form; se serve struttura, JSON o MD comparabili (Checksum) | ★ |
| Generazione di codice | Blocchi di codice free-form; o tool/function stretti per diff/edit | ★★ |
| Editing find-replace | Evita XML per il payload FR; formato diff JSON o MD | ★★ (Checksum) |
| Tool call multi-agente | JSON Schema di function-calling nativo, `strict: true` (OpenAI/Azure) o tool use con `strict: true` (Anthropic) | ★★★ |
| Dati tabellari | TOON solo per array uniformi; tabelle Markdown o CSV altrimenti; JSON per parsing a valle | ★★ |

### 3.3 Penalità di costo in token (input, stesso contenuto)

| Formato | Penalità ~ vs Markdown | Quando è giustificata |
|---|---|---|
| Markdown | 1,00× baseline | Default per documenti; default per scaffolding input su GPT |
| YAML | 1,10–1,13× | Dati annidati su modelli sensibili al formato (GPT-5 Nano, Gemini Flash Lite) |
| JSON | 1,51–1,60× | Contratti I/O strutturati; tool call; parsing a valle necessario |
| XML | **1,79–1,90×** | Partizionamento prompt specifico per Claude; wrapping di doc lunghi dove il valore del partizionamento supera il costo in token |
| Plain text | varia | Quando non serve struttura; baseline più semplice |

### 3.4 Riepilogo confidenza

- **Evidenza forte:** la scelta del formato può produrre swing di accuratezza a doppia cifra su modelli più piccoli/vecchi; l'output strutturato stretto danneggia il ragionamento open-weight; il rendering di immagini Markdown è un vettore di esfiltrazione importante; Lost-in-the-Middle persiste; i token di output costano 4–8× quelli di input.
- **Debole / conteso:** formato universalmente migliore (nessuno); se la scala "risolva" il format tax (i closed di frontiera sembrano averne chiuso buona parte); XML vs Markdown per la difesa dall'injection su modelli non-Claude.
- **Nessun dato:** studio controllato formato × lunghezza-contesto; effetti del formato sull'esito della cooperazione multi-agente; tabella audited token-per-byte su tutti i principali tokenizer e formati.

---

## 4. Tassonomia degli utilizzatori AI con analisi costo/beneficio

Tre categorie di utente, dalla più semplice alla più avanzata. Ciascuna ha una funzione obiettivo diversa su: accuratezza, affidabilità di parsing, costo in token, leggibilità umana, esposizione alla sicurezza, portabilità multi-modello. Le stesse tre categorie strutturano il protocollo di test (Sezione 5).

### A. Simple Prompt User
*Tier a pagamento, prompt scritti a mano, niente codice. Sa che il prompt conta; usa istruzioni base (ruolo, contesto, formato); conosce le differenze tra modelli a livello marketing.*
- **Obiettivo:** qualità e pulizia della risposta; sforzo minimo di formattazione.
- **Sensibilità al costo:** nulla (abbonamento flat).
- **Raccomandazione:** plain text o Markdown leggero come default. Su Claude, tag `<context>` / `<instructions>` quando il prompt ha più sezioni distinte; altrimenti prosa. Non chiedere JSON salvo copia-incolla verso un sistema a valle.
- **Costo/beneficio:** nessuna bolletta di token; i pochi token extra di una struttura leggera si ripagano in meno iterazioni *solo* se la struttura serve davvero (vedi D1).
- **Trappola principale:** incollare contenuto non fidato (email, pagine web) nella chat — superficie d'attacco dell'esfiltrazione via link-immagine Markdown.

### B. AI Engineer
*Chiama le API direttamente, scrive codice, conosce system prompt, temperature, token, few-shot, CoT. Costruisce app.*
- **Obiettivo:** affidabilità di parsing prima di tutto, poi accuratezza, poi costo.
- **Raccomandazione:**
  - *Output:* Structured Outputs nativi (`strict: true`) via tool/function calling per estrazione/classificazione/data-shaping. Mai chiedere "rispondi in JSON" via sola istruzione di prompt (vedi D3).
  - *Input:* Markdown su GPT; XML su Claude; YAML o Markdown per payload di config annidati passati come dati (vedi D5); per tabelle ampie, CSV/TOON sotto soglia di righe, JSON-records sopra (vedi D7tab).
  - *Ragionamento:* pattern a due passi — ragiona free-form, poi converti in JSON (vedi D4).
  - *Editing codice:* evita XML per i payload di find-replace (vedi D6).
- **Costo/beneficio:** paga l'overhead del JSON Schema solo sulla call finale, non su quella di ragionamento; i token di output costano molto più di quelli di input (vedi D10), quindi schemi stretti e oggetti appiattiti dove possibile.
- **Trappole:** sottoinsiemi di JSON Schema specifici per vendor (Gemini scarta feature non supportate in silenzio; OpenAI strict rifiuta `additionalProperties: true`); schemi ricorsivi non supportati; strict incompatibile con parallel tool calls (OpenAI) e con citazioni + prefill (Anthropic).

### C. AI Engineer Avanzato
*RAG pipeline, agenti multi-step, fine-tuning, embeddings, vector DB, evals. Ottimizza costi/latenza. Tool: LlamaIndex, LangSmith, HuggingFace, vLLM. Skill: architettura di sistemi AI, valutazione quantitativa.*
- **Obiettivo:** parsing affidabile, portabilità tra modelli, basso costo in token (lo stato si accumula), sicurezza (gli output di tool non fidati diventano input del turno dopo), observability.
- **Raccomandazione:**
  - *Tool call:* JSON Schema di function-calling nativo con `strict: true` ovunque supportato. Standardizzare su MCP / A2A / ACP / ANP per il traffico inter-agente (tutti JSON-RPC 2.0).
  - *Stato/scratchpad agente:* Markdown o YAML per l'ispezione umana; valutare forme compatte tipo pseudocodice per ridurre i token di stato (vedi D8); JSON solo al confine I/O dei tool.
  - *RAG:* wrapping dei chunk in XML `<document><source>` o formato a riga `ID|TITLE|CONTENT` su GPT; query alla fine; grounding quote-first (vedi D9, D11).
  - *Ragionamento:* tenerlo in NL free-form dentro `<thinking>` o via extended thinking — non legarlo a uno schema JSON.
  - *Caching:* design del prefisso stabile per massimizzare la cache esplicita Anthropic.
- **Costo/beneficio:** lo stato XML verboso si moltiplica tra i turni e fa esplodere la bolletta di input; preferire Markdown/compatto per la prosa e JSON solo al confine dei tool. Verificare il caso Claude+XML sui dati (ipotesi secondaria di D5) prima di standardizzare su un unico formato.
- **Trappole:**
  - **Trifecta letale** (Willison): dati privati + input non fidato + canale di esfiltrazione. Un agente che renderizza output di tool in una superficie Markdown con prefisso cached ha tutti e tre; togliere i link-immagine dagli output dei tool.
  - Tag-spoofing in input XML che sono anche output XML — usare tag con sale (AWS).
  - "JSON strutturalmente valido ≠ valori corretti" — ogni vendor garantisce solo la sintassi; serve validazione semantica.

### Tabella riassuntiva

| Categoria | Markup input di default | Formato output di default | Obiettivo primario | Trappola principale |
|---|---|---|---|---|
| **A** Simple Prompt User | Plain / MD leggero (XML su Claude se multi-sezione) | Free-form | Qualità e pulizia | Incollare contenuto non fidato |
| **B** AI Engineer | MD (GPT) / XML (Claude) + YAML per dati annidati; CSV/TOON o JSON per tabelle | JSON Schema strict via tool-mode | Affidabilità di parsing | Gap nei sottoinsiemi di schema dei vendor; format tax sul ragionamento |
| **C** AI Engineer Avanzato | Scaffolding MD + I/O JSON dei tool; XML `<document>` per RAG | Tool/function call strict | Portabilità + costo + sicurezza | Trifecta letale; stato verboso che esplode in token |

---
## 5. Protocollo di benchmark (da eseguire dopo)

Progettato per riproducibilità, controllo dei confondenti e predizioni esplicite falsificabili. Le domande sono organizzate per **categoria di utente**, dal più semplice al più avanzato, perché lo scopo del documento (e dell'articolo che ne deriverà) è dare a ciascun profilo le poche regole operative che gli servono davvero, non rispondere a ogni domanda accademica possibile. Implementazione prevista: PromptFoo (harness multi-modello) + Pydantic (validazione schema) + scoring custom.

### 5.1 Modelli sotto test

Solo modelli **attualmente in produzione**, per contenere i costi di esecuzione. Tutti raggiunti via API.

| Famiglia | Modello | Ruolo nel test |
|---|---|---|
| OpenAI | GPT-5.5 | Frontiera OpenAI (rilasciato apr 2026, focus agentico) |
| OpenAI | GPT-5.4 | OpenAI generazione precedente (rilasciato mar 2026; confronto intra-vendor) |
| Anthropic | Claude Opus 4.8 | Frontiera Anthropic |
| Anthropic | Claude Sonnet 4.6 | Fascia media Anthropic |
| Anthropic | Claude Haiku 4.5 | Fascia veloce/economica Anthropic |
| Open-weight (locale) | Qwen2.5 (via Ollama) | Riferimento open-weight/locale; usato spesso come fallback e orchestratore locale |

**Sul parametro di reasoning/effort:** tutti i modelli vengono eseguiti a un livello di effort/reasoning **medio** come default fisso, per non confondere la variabile-formato con la variabile-effort. OpenAI espone `reasoning_effort` (si usa `medium`); Anthropic espone l'extended thinking con budget di token (si fissa un budget intermedio equivalente); Qwen via Ollama si esegue con la sua configurazione di reasoning di default a livello comparabile. **Eccezione:** in D3 e D4 l'effort diventa una **variabile esplicita** testata a più livelli (vedi quei due esperimenti), perché tocca direttamente il ragionamento e potrebbe interagire con il vincolo di output — fissarlo lì nasconderebbe l'effetto che quei due esperimenti vogliono misurare.

**Limite esplicito del protocollo:** la presenza di **un solo** modello open-weight/locale (Qwen2.5) e l'assenza di modelli piccoli/vecchi significano che questo protocollo offre un confronto open-vs-closed solo **indicativo**, non sistematico. Qwen permette di vedere se le tendenze osservate sui modelli closed di frontiera reggono anche su un open-weight locale (ed è il modello che l'utente usa davvero come fallback/orchestratore), ma un singolo punto open non basta a caratterizzare il "format tax" legato alla scala: per quello resta valida l'evidenza esistente (Format Tax 2026, He et al.), dove i modelli open-weight perdono accuratezza sostanziale sotto vincoli di formato stretti mentre i frontiera closed no. I risultati su Qwen vanno quindi letti come segnale sul caso d'uso specifico dell'utente, non come misura generale dei modelli open. Inoltre Qwen via Ollama **non** dispone di structured output garantito a livello di vendor come quello nativo di OpenAI/Anthropic: negli esperimenti Q-OUT che usano lo structured output nativo (D3) Qwen va trattato a parte (output strutturato ottenibile solo via libreria di constrained decoding lato Ollama o via istruzione, da dichiarare nel risultato).

### 5.2 Principi di design

1. Separare gli esperimenti **Q-IN** (formato dell'input) da quelli **Q-OUT** (formato dell'output). Mai variare entrambi nello stesso confronto.
2. Tenere il contenuto identico tra le condizioni di formato; cambia solo il wrapper di markup. Canonicalizzare via una singola rappresentazione sorgente, resa in ciascun formato da una funzione di templating deterministica.
3. Fissare per ogni formato uno stile costante di separatore, casing e spaziatura, così che la variabile sotto test sia il formato e non micro-dettagli tipografici.
4. Pre-registrare le ipotesi con predizioni direzionali prima di eseguire; riportare gli effetti osservati con intervalli di confidenza al 95%.
5. ≥3 seed per cella dove il modello espone la temperature; per i modelli reasoning senza temperature, ≥3 call ripetute. Effort/reasoning fissato a medio per tutti (eccetto D3 e D4, dove è variabile).
6. Conteggio token per call (input + output) col contatore ufficiale di ciascun vendor (tiktoken per OpenAI, count_tokens API per Anthropic, tokenizer del modello via Ollama per Qwen).
7. Costo in USD ai prezzi per-token in vigore al momento del run; input e output contati separatamente.
8. Risultati sempre riportati **per modello**, mai aggregati tra vendor.
9. **Criterio di falsificazione comune:** un'ipotesi è considerata smentita se il risultato reale è fuori dalla direzione prevista a p<0,01 con effect size |δ|>0,1 (Wilcoxon signed-rank su item appaiati; correzione Bonferroni sui confronti multipli di formato all'interno di uno stesso task).

---

### 5.3 Categoria A — Simple Prompt User

*Profilo: usa tier a pagamento, scrive prompt a mano, niente codice. Sa che il prompt conta. Usa istruzioni base (ruolo, contesto, formato). Conosce le differenze tra modelli a livello marketing.*

La domanda di fondo di questo utente è: **quanto di tutto questo lo riguarda davvero, e cosa può tranquillamente ignorare?**

#### D1 — La struttura del prompt cambia davvero l'accuratezza ai miei usi?
- **Cosa testa [Q-IN]:** stesso compito di classificazione, dato al modello in tre vesti — prosa libera, Markdown con sezioni, tag XML — a contenuto identico.
- **Come:** Suite Classificazione (500 item: MMLU stratificato, DDXPlus, Sports). 3 seed. Si misura l'accuratezza per formato su tutti e sei i modelli.
- **Ipotesi:** sui modelli di frontiera attuali lo spread tra il miglior e il peggior formato di input è piccolo (≤2 pp su GPT-5.5 e Opus 4.8; eventualmente un po' più ampio su Haiku 4.5).
- **Perché conta:** dice a questo utente se "fare il prompt per bene" è una competenza che gli rende o folklore. Se lo spread è minimo, il messaggio è liberatorio: scrivi chiaro in prosa e non perdere tempo a taggare. Se è ampio, è il segnale che la struttura va curata.

#### D2 — Quale formato di input conviene per prompt istruzione-pesanti, e l'XML raccomandato da Anthropic è davvero il migliore su Claude?
- **Cosa testa [Q-IN]:** stesso prompt istruzione-pesante reso nei cinque formati non-tabellari — plain text, Markdown, XML, JSON, YAML — su tutti e sei i modelli (non solo Claude). La domanda specifica su Anthropic (XML vs Markdown su Claude) diventa un caso particolare letto dentro un confronto completo.
- **Come:** sottoinsieme della Suite Classificazione + un set di task istruzione-pesanti (prompt con più sezioni: ruolo, contesto, istruzioni, esempi). Si misura l'accuratezza per formato e per modello, più i token.
- **Ipotesi:** su Claude l'XML dà un vantaggio piccolo ma positivo rispetto a Markdown su prompt multi-sezione, e non è il peggiore; su GPT prevale Markdown; su Qwen l'effetto è più marcato che sui frontiera closed. Su prompt semplici i formati convergono.
- **Perché conta:** Anthropic raccomanda XML, ma per chi scrive a mano imparare i tag è un costo. Testare tutti i formati su tutti i modelli dice se la raccomandazione regge in un confronto completo e se vale solo per Claude o anche altrove. (CSV/TOON esclusi: il contenuto non è tabellare.)

#### D11 — La posizione delle istruzioni nel prompt cambia il risultato? (e i vendor si contraddicono)
- **Cosa testa [Q-IN]:** stesso prompt lungo con le istruzioni messe in tre posizioni — solo all'inizio, solo alla fine (dopo i dati), a entrambe le estremità.
- **Come:** Suite Contesto lungo (vedi D9) riusata con questa variabile; documenti di lunghezza fissa, istruzione identica spostata. Si misura l'accuratezza per posizione.
- **Ipotesi:** "istruzioni alla fine, dopo i dati" eguaglia o batte "solo all'inizio" su tutti i modelli; "entrambe le estremità" non fa peggio di "solo fine". (Le guide ufficiali si contraddicono: OpenAI dice entrambe le estremità, Gemini e Anthropic dicono fine.)
- **Perché conta:** è una leva a costo zero — non aggiunge token, è solo *dove* metti il testo — e riguarda tutti i livelli. Mette alla prova le prescrizioni ufficiali dei vendor una contro l'altra, cosa che nessuno studio pubblicato ha fatto.

---

### 5.4 Categoria B — AI Engineer

*Profilo: chiama le API direttamente, scrive codice, conosce system prompt, temperature, token, few-shot, CoT. Costruisce app.*

Le sue domande sono decisioni di codice: come strutturare le call perché l'app sia affidabile ed economica.

#### D3 — Per output che il mio codice può parsare, servono gli structured output nativi o basta chiedere "rispondi in JSON" nel prompt? (e quanto incide l'effort)
- **Cosa testa [Q-OUT]:** stesso compito di estrazione in due modi — (a) JSON Schema strict / structured output nativi del vendor, (b) sola istruzione testuale nel prompt che chiede JSON, senza vincolo nativo. **L'effort qui è una variabile:** ogni modalità viene testata a effort basso/medio/alto (OpenAI `reasoning_effort`; Anthropic budget di extended thinking; Qwen configurazione equivalente via Ollama), per vedere se alzare il ragionamento migliora la compliance del prompt-only fino a chiudere il divario col nativo.
- **Come:** Suite Estrazione (5 schemi × 60 documenti). Si misura la percentuale di risposte che il parser Pydantic accetta al primo tentativo, per modello, modalità e livello di effort. **Qwen** non ha structured output nativo a livello vendor: la modalità (a) per Qwen va ottenuta via constrained decoding lato Ollama (o, se non disponibile, marcata come non confrontabile e tenuta fuori dal confronto nativo).
- **Ipotesi:** strict/nativo ≥99% di parsing riuscito a ogni livello di effort; prompt-only 85–95% a effort medio, con un miglioramento ad alto effort che però **non** raggiunge il nativo. Il margine è ampio su tutti i modelli closed; su Qwen il prompt-only parte più in basso.
- **Perché conta:** è la differenza tra un'app che si rompe nel 5–15% dei casi e una che si rompe in meno dello 0,1%. Testare anche l'effort dice se "basta far ragionare di più il modello" è un'alternativa al vincolo nativo (ipotesi: no). È la verifica che giustifica l'adozione degli structured output invece di parsare a mano con try/except e regex fragili.

#### D4 — Quando il compito richiede ragionamento, forzo il JSON da subito o faccio ragionare libero e poi converto? (e quanto incide l'effort)
- **Cosa testa [Q-OUT]:** su task di ragionamento, due pipeline a confronto — una sola call che produce direttamente JSON strict, contro due passi (prima ragionamento in linguaggio naturale libero, poi una seconda call che incassa il risultato in JSON). **L'effort qui è una variabile:** entrambe le pipeline testate a effort basso/medio/alto. È l'interazione più interessante del protocollo, perché alzare l'effort fa ragionare di più il modello *internamente* e potrebbe rendere il vincolo JSON-diretto meno penalizzante, riducendo il vantaggio del due-passi.
- **Come:** Suite Ragionamento (GSM8K, ZebraLogic, MATH-500; 300 item ciascuna). Si misura l'accuratezza del risultato finale per pipeline e per livello di effort, su tutti e sei i modelli.
- **Ipotesi:** a effort basso/medio il pattern a due passi batte il JSON strict diretto di ≥5 pp su tutti i modelli; ad alto effort il divario si riduce sui frontiera closed (che ragionano molto internamente) ma resta su Qwen. In nessun caso il JSON-diretto supera il due-passi.
- **Perché conta:** decide la forma delle tue call quando c'è logica di mezzo. Se il due-passi vince a effort medio (il default), conviene spendere una call in più per non perdere accuratezza; se ad alto effort il divario sparisce, l'alternativa diventa "una sola call ad alto effort" — ma a costo maggiore. (Ancora: Tam 2024 e Format Tax 2026 — non coprono i modelli attuali né l'interazione con l'effort.)

#### D5 — Come conviene impacchettare i dati strutturati che metto dentro il prompt? (con lettura specifica su Claude+XML)
- **Cosa testa [Q-IN]:** stessi dati (oggetti annidati, config) passati nel prompt nei cinque formati non-tabellari — plain text, Markdown, XML, JSON, YAML — su tutti e sei i modelli.
- **Come:** Suite Dati annidati (config Terraform-like, 6–7 livelli, calibrata alla fascia 40–60% di accuratezza; ~1.000 domande per cella). Si misura accuratezza delle risposte e token consumati, per formato e modello.
- **Ipotesi primaria (confronto generale):** YAML e Markdown più economici (in token) e in genere più accurati di JSON e XML su GPT e Qwen. Plain text debole sui dati molto annidati (perde la struttura).
- **Ipotesi secondaria (lettura Claude, valutata sugli stessi dati, senza chiamate aggiuntive):** sul sottoinsieme dei tre modelli Claude, XML **non** è il peggiore — a differenza del pattern generale è alla pari di YAML e Markdown, e sopra JSON. *Contesto:* sulla maggior parte dei modelli XML è il formato peggiore per i dati annidati profondi, sia in accuratezza sia in costo (~+80% di token vs Markdown), ma Claude è addestrato con moltissimo XML (formato nativo del suo tool-use) e potrebbe reggerlo meglio. Nessuno studio pubblicato ha verificato questo su Claude: è la parte più originale dell'esperimento, e si ottiene filtrando i risultati di D5 sui modelli Claude — non serve un esperimento separato.
- **Perché conta:** è una decisione che prendi ogni volta che dai dati in pasto a un prompt, e tocca due cose insieme — quanto bene il modello li capisce e quanto ti costano. Stabilisce il formato-dato di default per le tue chiamate. La lettura Claude in più decide una cosa specifica per chi costruisce su Claude: se XML penalizza anche lì, la regola diventa "XML per partizionare il prompt, ma YAML/Markdown per i dati dentro"; se Claude regge l'XML sui dati, puoi restare coerente con un solo formato. (CSV/TOON esclusi: i dati sono annidati, non tabellari — quelli sono coperti da D7tab.)

#### D6 — Per far modificare codice al modello (find-replace, diff), quale formato di output regge meglio?
- **Cosa testa [Q-OUT]:** bug da correggere chiedendo l'output di modifica in tutti i formati di output applicabili a una patch — Markdown (diff/blocco), XML, JSON, YAML, plain text (diff unificato) — su tutti e sei i modelli; il codice risultante viene eseguito sui test. **Nota sull'impostazione Q-OUT:** solo il JSON può usare lo structured output nativo; gli altri formati si ottengono via istruzione testuale, quindi il confronto è "JSON nativo-strict vs altri-via-prompt" e va letto come tale, non come parità di condizioni.
- **Come:** Suite Editing find-replace (30 bug costruiti a mano, N=30 per cella, replica del protocollo Checksum). Si misura il pass-rate dei test per formato e modello.
- **Ipotesi:** l'output XML resta in fondo sul find-replace (≥10 pp sotto il migliore: XML fatica a esprimere pattern di match esatto); plain-text-diff e Markdown-diff competitivi; JSON intermedio.
- **Perché conta:** se costruisci tool che editano codice, il formato in cui chiedi la patch incide sulla riuscita. Verifica sui modelli in produzione un effetto finora visto solo su Haiku 4.5 in un singolo blog (Checksum). (CSV/TOON esclusi: una patch di codice non è una tabella.)

#### D7tab — Quanto degradano i modelli sui dati tabellari ampi, e quale formato regge? *(E7)*
- **Cosa testa [Q-IN]:** stessa tabella passata nel prompt in quattro rappresentazioni testuali — Markdown table, CSV, JSON records, TOON — a dimensioni crescenti (50, 500, 2.000, 5.000 righe).
- **Esempio del dato (3 righe su migliaia):**
  - *Markdown table:* `| order_id | region | amount | margin_pct | quarter |` + righe con `|` e allineamento.
  - *CSV:* header `order_id,region,amount,margin_pct,quarter` + righe di soli valori.
  - *JSON records:* `[{"order_id":1001,"region":"North",...}, ...]` — ripete tutte le chiavi a ogni riga.
  - *TOON:* `[N]{order_id,region,amount,margin_pct,quarter}:` + righe di soli valori — dichiara le colonne una volta sola.
- **Come:** per ogni dimensione e formato, tre tipi di domanda: lookup puntuale ("qual è il margin_pct dell'ordine 3847?"), aggregazione ("somma degli amount per regione North"), filtro+conteggio ("quanti ordini Q3 sopra 1000€?"). Si misura accuratezza per formato × dimensione × tipo di domanda, più i token consumati. L'output interessante è la **curva**: il punto di righe in cui la rappresentazione compatta comincia a sbagliare.
- **Ipotesi:** fino a qualche centinaio di righe i formati sono equivalenti in accuratezza, quindi vince il più economico (CSV o TOON); oltre una soglia di righe i formati compatti perdono accuratezza più dei verbosi, in particolare sul lookup puntuale, aprendo un trade-off costo/accuratezza oggi non mappato sui modelli in produzione. TOON va forte solo sul suo caso ideale (tabella piatta uniforme) e meno altrove.
- **Perché conta:** far ragionare un LLM su output tabellari (risultati di query, estratti Excel, righe di DB) è il caso d'uso più vicino al data engineering, ed è quello in cui i conti dei token diventano seri perché le tabelle sono grandi. La regola che ne esce — "sotto N righe usa CSV/TOON e risparmi, sopra N passa a JSON-records o spezza la tabella" — è direttamente azionabile. *Limite:* se i casi reali stanno quasi sempre sotto le poche centinaia di righe, o se la tabella si passa come file da elaborare con codice invece che come testo nel prompt, il valore di questo test cala.

---

### 5.5 Categoria C — AI Engineer Avanzato

*Profilo: RAG pipeline, agenti multi-step, fine-tuning, embeddings, vector DB, evals. Ottimizza costi/latenza. Tool: LlamaIndex, LangSmith, HuggingFace, vLLM. Skill: architettura di sistemi AI, valutazione quantitativa.*

> La domanda "su Claude+XML i dati annidati" che in una versione precedente era un esperimento separato (D7) è ora l'ipotesi secondaria di **D5** (Categoria B): si valuta sugli stessi dati filtrando i risultati sui modelli Claude, senza chiamate aggiuntive.

#### D8 — Per lo stato che gli agenti si passano tra loro, un formato compatto fa risparmiare abbastanza token da valerne la pena?
- **Il contesto del problema:** in un sistema multi-agente, a ogni passo gli agenti si passano lo "stato" (cosa è stato fatto, risultati intermedi, piano). Se è in JSON verboso, ogni turno aggiunge token e su workflow lunghi il conto di input esplode, perché lo stato si accumula e viene rielaborato a ogni passo. Un approccio studiato in "CodeAgents" codifica lo stato in **pseudocodice compatto** invece che in JSON, mostrando tagli di token molto grandi su un benchmark agentico.
- **Cosa testa [Q-IN + Q-OUT]:** task multi-step in stile agentico, orchestratore tenuto fisso (LangGraph), stesso workflow con lo stato passato in tutti i formati applicabili — JSON, Markdown, YAML, XML, plain text, più una forma compatta tipo pseudocodice; si misurano token di input totali e success rate (task completate correttamente). Su tutti e sei i modelli.
- **Come:** Suite Multi-agente (50 task stile GAIA). 3 run.
- **Ipotesi specifica:** la forma compatta (pseudocodice) e YAML tagliano i token di input in modo netto vs JSON e XML (compatto ≥40% sotto JSON), **senza** far calare il success rate di più di 3 pp; XML lo stato più costoso.
- **Perché conta:** è economia diretta dei tuoi sistemi. Se vero, riduci molto i costi di input di un sistema multi-agente cambiando solo come codifichi lo stato, a parità di risultato. Se il risparmio si paga in affidabilità persa, il formato verboso ma robusto resta la scelta giusta — e lo sai. *Caveat sull'ancora:* lo studio CodeAgents confonde formato, brevità e decomposizione multi-agente, e usa una baseline debole; questo test isola meglio la variabile formato. (CSV/TOON esclusi: lo stato di un agente non è una tabella uniforme.)

#### D9 — Per i documenti recuperati in una pipeline RAG, conviene avvolgerli in tag XML o passarli come array JSON?
- **Il contesto del problema:** in RAG recuperi N pezzi di documento dal vector DB e li impacchetti nel prompt prima di chiedere al modello di rispondere citando le fonti. Due modi tipici: avvolgere ogni pezzo in tag XML (`<document><source>…</source><document_content>…</document_content></document>`) oppure passarli come lista JSON di oggetti. La guida ufficiale OpenAI afferma che nei loro test a contesto lungo l'array JSON ha reso **particolarmente male** e il wrapping XML bene — ma è un'affermazione interna, non verificata da terzi né testata su Claude.
- **Cosa testa [Q-IN]:** stesso set di documenti recuperati e stesse domande, avvolti nei cinque formati non-tabellari — XML `<document>`, array JSON, Markdown (heading + metadati), YAML, plain text con delimitatori; si misura accuratezza delle risposte e, dove possibile, fedeltà delle citazioni, su tutti e sei i modelli.
- **Come:** Suite Contesto lungo (200 item × lunghezze 8K/32K/128K, e 1M dove supportato), con questa variabile di wrapping.
- **Ipotesi specifica:** il wrapping XML e quello Markdown battono l'array JSON di ≥7 pp su ogni modello (replicando la tesi OpenAI "JSON scarso per contesto lungo"); plain text il più debole sui contesti molto lunghi.
- **Perché conta:** è una decisione di architettura RAG che prendi una volta e che poi vale per ogni query del sistema. Se XML/Markdown vincono in modo netto e consistente, sono la scelta di default per il packing dei chunk; se la differenza è piccola, scegli in base ad altri criteri (parsing, leggibilità dei log). (CSV/TOON esclusi: i chunk sono documenti testuali, non righe tabellari.)

#### D10 — Quanto pesano davvero i token di output rispetto a quelli di input, e quale formato di output è più economico?
- **Cosa testa [economia]:** ai prezzi di listino dei vendor, due cose insieme — (a) il rapporto di costo tra un token di output e uno di input; (b) il costo relativo dei diversi formati di output a parità di informazione resa (JSON strict nativo vs gli altri formati ottenuti via istruzione: Markdown, YAML, XML, plain text). Su tutti e sei i modelli.
- **Come:** strumentazione di costo su tutte le suite Q-OUT; calcolo costo = (token_in × tariffa_in) + (token_out × tariffa_out) per modello e per formato di output. Per Qwen locale il "costo" è espresso in token e tempo, non in tariffa vendor (da segnalare separatamente).
- **Ipotesi specifica:** i token di output costano ≥4× quelli di input su tutti i modelli closed; tra i formati di output, XML il più costoso in token e YAML/plain tra i più economici, con JSON intermedio ma con il vantaggio della garanzia nativa.
- **Perché conta:** governa il budget dell'intero sistema. Se il rapporto output/input è confermato, la regola operativa è "tieni gli schemi di output il più stretti possibile, appiattisci dove puoi, non chiedere campi che puoi derivare a valle"; e la scelta del formato di output diventa anche una scelta di costo, non solo di parsing. Per chi ottimizza costi/latenza è una delle leve a impatto maggiore.

---

### 5.7 Mappa domande × suite × categoria

| Domanda | Categoria | Suite | Q-IN / Q-OUT | Stato dell'ancora |
|---|---|---|---|---|
| D1 struttura conta | A | Classificazione | Q-IN | He et al. `[LEGACY]` |
| D2 XML su Claude | A | Classificazione + istruzione-pesanti | Q-IN | doc Anthropic; Tam `[LEGACY]` |
| D11 posizione istruzioni | A | Contesto lungo | Q-IN | guide vendor (contraddittorie) |
| D3 structured vs prompt-only | B | Estrazione | Q-OUT | OpenAI; JSONSchemaBench |
| D4 ragiona-poi-converti | B | Ragionamento | Q-OUT | Tam, Format Tax `[PROD]` parziale |
| D5 formato dati nel prompt (+ lettura Claude+XML) | B | Dati annidati | Q-IN | ImprovingAgents `[PROD]`; lettura Claude = buco |
| D6 editing codice | B | Find-replace | Q-OUT | Checksum `[PROD]` |
| D7tab tabelle ampie (E7) | B | Tabellare (nuova) | Q-IN | nessuna (buco) |
| D8 stato agenti compatto | C | Multi-agente | Q-IN+OUT | CodeAgents (con caveat) |
| D9 wrapping RAG XML vs JSON | C | Contesto lungo | Q-IN | OpenAI (non verificato terzi) |
| D10 economia output | C | trasversale Q-OUT | economia | prezzi pubblici |

### 5.8 Suite di task (specifiche)

I formati testati per ciascuna suite seguono la regola dell'**applicabilità al tipo di contenuto**: i cinque formati non-tabellari (plain, Markdown, XML, JSON, YAML) sui contenuti testuali/annidati; i sette completi (i cinque + CSV + TOON) solo sui contenuti tabellari.

- **Classificazione:** 500 item — MMLU stratificato (10 materie × 50), DDXPlus medico (500), Sports/BIG-Bench (500). Formati: cinque non-tabellari. Metrica: accuratezza, substring match su gold canonicalizzato.
- **Ragionamento:** 300 item ciascuna — GSM8K, ZebraLogic, MATH-500. Formati: cinque non-tabellari (Q-IN); per D4 le due pipeline × tre livelli di effort. Metrica: accuratezza del risultato finale.
- **Estrazione:** 5 schemi × 60 documenti (protocollo ExtractBench). Q-OUT: nativo-strict vs prompt-only × tre livelli di effort (D3). Metrica: F1 a livello di campo + tasso di compliance Pydantic al primo tentativo.
- **Find-replace:** 30 bug costruiti a mano, N=30 per cella. Q-OUT: formati di patch (Markdown, XML, JSON, YAML, plain-diff) via istruzione, JSON anche nativo. Metrica: pass@1 via esecuzione test.
- **Dati annidati:** config Terraform-like (6–7 livelli), ~1.000 domande per cella, calibrate a 40–60%. Formati: cinque non-tabellari. Metrica: accuratezza (substring) + token.
- **Tabellare (nuova):** tabelle a 50/500/2.000/5.000 righe × **sette formati** {plain, Markdown table, XML, JSON records, YAML, CSV, TOON} × {lookup, aggregazione, filtro+conteggio}. Metrica: accuratezza + token; output = curva accuratezza/righe.
- **Contesto lungo:** 200 item × lunghezze 8K/32K/128K (+1M dove supportato); usata sia per D9 (wrapping, cinque formati non-tabellari) sia per D11 (posizione istruzioni). Metrica: accuratezza + fedeltà citazioni.
- **Multi-agente:** 50 task stile GAIA, orchestratore LangGraph fisso. Stato in cinque formati non-tabellari + forma compatta pseudocodice. Metrica: success rate + token input totali + costo.

### 5.9 Metriche e statistica

- **Accuratezza / exact-match:** substring su gold canonicalizzato; F1 a livello di campo per l'estrazione.
- **Pass@1:** esecuzione automatica di unit test (codice, find-replace).
- **Giudice LLM** (task generativi): modello di vendor diverso dall'esecutore, per evitare il bias same-family visto in Checksum; calibrato a ≥95% di accordo umano su un sottocampione di 100. (Per i task con esecutore Qwen, giudice closed di uno dei due vendor.)
- **Compliance schema (Q-OUT):** % di risposte che passano la validazione Pydantic al primo tentativo.
- **Token e costo:** input, output, input cached separati; costo a listino per i modelli closed, in token+tempo per Qwen locale (segnalato a parte).
- **Test statistici:** Wilcoxon signed-rank su item appaiati; Bonferroni sui confronti multipli (con sette formati i confronti per task crescono — la correzione va ricalibrata di conseguenza); effect size Cliff's δ accanto ai p-value. Mai confronti "X>Y" tra modelli (troppi confondenti): sempre per modello. Numerosità (300–1.000 per cella) → >90% di potenza per differenze di 5 pp ad α=0,01.

### 5.10 Confondenti controllati

- Bias posizionale: ruotare l'ordine delle opzioni in classificazione; randomizzare la posizione del needle nel contesto lungo (eccetto in D11, dove la posizione è la variabile).
- Micro-variazioni: stile di separatore/casing/spaziatura fissato per formato.
- Effort/reasoning: fissato a medio per tutti gli esperimenti tranne D3 e D4, dove è la variabile.
- Bias del tokenizer: token contati col tool ufficiale di ciascun vendor (tiktoken / count_tokens / tokenizer Ollama); mai confronti di token diretti tra vendor.
- Bias del giudice same-family: giudice di vendor diverso dall'esecutore.
- Caching: cache pulita tra condizioni; tassi di token cached riportati a parte (Qwen locale non ha caching vendor).
- Drift versione/orario: tutti i formati per una data coppia (modello, task) eseguiti in un singolo batch entro 24 ore; snapshot di versione registrato. Per Qwen, versione del modello e del runtime Ollama registrate.

### 5.11 Tooling (secondario)

PromptFoo (orchestrazione multi-modello, export JSON per call); Pydantic (validazione schema, metrica Q-OUT); tiktoken / count_tokens API / tokenizer via Ollama (conteggio per modello); strict mode nativo dei vendor per i confronti Q-OUT su modelli closed, constrained decoding lato Ollama per Qwen dove disponibile; Ollama come runtime per Qwen2.5 in locale; Python (statsmodels, scipy) per Wilcoxon e Cliff's δ, con notebook dei risultati e dati grezzi pubblicati.

## 6. Bibliografia annotata

Tier: **T1** peer-reviewed; **T2** preprint arXiv con metodo solido; **T3** blog tecnico con esperimento empirico; **T4** documentazione vendor; **T5** opinione/illustrativo. `[PROD]` = testa modelli in produzione. `[LEGACY]` = modelli fuori produzione, mantenuto come base T1.

### Studi prioritari su modelli in produzione
1. **Lee, D'Antoni & Berg-Kirkpatrick 2026** — "The Format Tax." arXiv 2604.03616. **T2 `[PROD]`.** 10 modelli × 5 formati; il costo entra al prompt; il disaccoppiamento recupera; i frontiera closed mostrano tax minimo.
2. **Checksum.ai — Gal Vered, 2 dic 2025.** checksum.ai/blog/does-output-format-actually-matter... **T3 `[PROD]`.** 90 run su Claude Haiku 4.5; JSON vince a sorpresa la creativa; XML peggiore sul find-replace. Caveat: N=10/cella, esecutore e giudice same-family.
3. **ImprovingAgents, 14 ott 2025.** improvingagents.com/blog/best-nested-data-format. **T3 `[PROD]`.** 1.000 domande × GPT-5 Nano / Gemini 2.5 Flash Lite / Llama 3.2; YAML > MD > JSON > XML su dati annidati; XML ~+80% token. Caveat: singolo dominio; substring matching.
4. **ImprovingAgents — TOON benchmarks.** improvingagents.com/blog/toon-benchmarks. **T3 `[PROD]`.** TOON ultimo sui dati annidati; competitivo solo su array uniformi.
5. **Chroma (Hong, Troynikov, Huber) 2025** — "Context Rot." research.trychroma.com/context-rot. **T2/T3 `[PROD]`.** Degrado su 18 modelli (Claude 4, GPT-4.1, Gemini 2.5). Caveat: vendor RAG.
6. **The Structured Output Benchmark 2026** — arXiv 2604.25359. **T2 `[PROD]`.** ExtractBench (4,6% field-level pass), StructEval, DeepJSONEval.
7. **Geng et al. 2025** — JSONSchemaBench. arXiv 2501.10868. **T2.** I modelli di frontiera ancora falliscono JSON valido su schemi non banali.
8. **Pinto-Coelho et al. 2025** — "Structured Prompts Improve Evaluation of LMs" (DSPy+HELM). arXiv 2511.20836. **T2.** +6% medio su HELM; ranking cambia su 5/7 benchmark.
9. **"Flaw or Artifact?" 2025** — arXiv 2509.01790. **T2.** Buona parte della sensibilità è artefatto di valutazione.

### Studi fondanti su modelli legacy (mantenuti)
10. **He et al. 2024** — "Does Prompt Formatting Have Any Impact on LLM Performance?" arXiv 2411.10541. **T2 `[LEGACY]`.** 4 modelli GPT × 4 formati (plain/MD/YAML/JSON) su 6 task. Fonte della cifra 42% MMLU. Caveat: niente XML/HTML; solo GPT.
11. **Tam et al. 2024** — "Let Me Speak Freely?" arXiv 2408.02442; EMNLP 2024 Industry. **T1 `[LEGACY]`.** Base T1 per Q-OUT; l'output stretto degrada il ragionamento, aiuta la classificazione; Claude preferisce XML.
12. **Sclar et al. 2024** — FormatSpread. arXiv 2310.11324; ICLR 2024. **T1 `[LEGACY]`.** Spread fino a 76 pt con perturbazioni atomiche; i template non trasferiscono tra modelli.
13. **Liu et al. 2023** — "Lost in the Middle." arXiv 2307.03172; TACL 12 (2024). **T1 `[LEGACY]`.** U-shape nel contesto lungo; confermata da Chroma 2025 sui modelli attuali.

### Documentazione vendor (T4)
14. **Anthropic — XML tags guide.** docs.claude.com/.../prompt-engineering/use-xml-tags.
15. **Anthropic — Claude 4.x best practices.** docs.claude.com/.../claude-4-best-practices.
16. **Anthropic — Long-context tips.** docs.claude.com/.../long-context-tips. Pretesa "+30% con query alla fine".
17. **Anthropic — Structured Outputs.** docs.claude.com/.../structured-outputs (GA 4 feb 2026).
18. **Anthropic — Tool use.** platform.claude.com/docs/.../implement-tool-use. Semantica `strict: true`.
19. **Anthropic — Prompt caching.** Fino a 90% costo / 85% latenza in meno su prefissi cached.
20. **OpenAI — GPT-4.1 prompting guide.** cookbook.openai.com, 14 apr 2025. Primo ranking esplicito (MD > XML > JSON).
21. **OpenAI — GPT-5 / 5.1 / 5.2 prompting guides.** cookbook.openai.com. Blocchi spec a tag XML negli esempi.
22. **OpenAI — Structured Outputs.** platform.openai.com/docs/guides/structured-outputs. Pretesa 100% su gpt-4o-2024-08-06.
23. **OpenAI — Function calling.** platform.openai.com/docs/guides/function-calling. "Abilita sempre la strict mode."
24. **Google — Gemini prompt design strategies.** ai.google.dev/gemini-api/docs/prompting-strategies (28 apr 2026).
25. **Google — Gemini 3 doc.** ai.google.dev/gemini-api/docs/gemini-3. "Istruzioni alla fine."
26. **Google — Structured output.** ai.google.dev/gemini-api/docs/structured-output. Garanzia solo sintattica.
27. **Google — Gemini Nano prompt design.** developers.google.com/ml-kit/genai/... Guida esplicita `##` + `<tag>`.
28. **Google — Vertex AI controlled generation.** "I modelli tuned possono degradare con l'output strutturato."
29. **Microsoft — Azure prompt engineering / structured outputs.** learn.microsoft.com/.../prompt-engineering. Eredita OpenAI.

### Agenti e protocolli agent-to-agent
30. **CodeAgents (Yang et al. 2025)** — "Token-Efficient Codified Multi-Agent Reasoning." arXiv 2507.03254. **T2.** Prompt in pseudocodice Python: +10,7 pp / −67,8% token / −67,4% costo su GAIA L1 con Gemini-2.5-Flash. Caveat: baseline NL debole; formato confuso con brevità e decomposizione multi-agente.
31. **MCP (Anthropic, Linux Foundation 2025).** Richiede risultati di tool strutturati conformi a schema di output (spec nov 2025).
32. **A2A (Google → LF giu 2025), ACP (IBM), ANP** — tutti JSON-RPC 2.0. Convenzioni di traffico inter-agente.
33. **OWASP LLM Top 10 (2025).** genai.owasp.org/llm-top-10. LLM01 Prompt Injection; LLM05 Improper Output Handling.

### Sicurezza (cite con cautela)
34. **Simon Willison — prompt injection tag.** simonwillison.net/tags/prompt-injection. **T5 ma autorevole sugli incidenti.** Vettore di esfiltrazione via immagini Markdown; "trifecta letale".
35. **Schneidenbach — XML vs Markdown injection test.** schneidenba.ch/testing-llm-prompt-injection-defenses. **T3.** 480 test; differenza minima sui modelli OpenAI.
36. **AWS prescriptive guidance — LLM prompt-engineering best practices.** docs.aws.amazon.com/.../best-practices. **T4.** Pattern dei tag XML con sale.

### Risultati negativi (pretese investigate e non trovate)
37. **"OpenAI 73% preferenza degli annotatori umani per prompt strutturati"** — risale a una sola fonte secondaria. Nessuna fonte primaria OpenAI (Cookbook, blog, paper) la sostiene. **Stato: non verificata; da trattare come apocrifa finché non emerge una fonte primaria.**
38. **"Anthropic internal testing: prompt XML strutturati 20–40% più consistenti"** — trovata in riassunti di terzi attribuiti a una "Anthropic Prompt Engineering Guide, 2025". Non localizzata nella documentazione Anthropic attuale. **Da trattare come non verificata.**

---

## 7. Domande aperte ad alta priorità

Le domande falsificabili oggi senza risposta che il protocollo (Sezione 5) è progettato per affrontare.

1. **Lo spread di formato cresce in modo monotòno con la lunghezza del contesto?** (H13) — nessuno studio pubblicato incrocia formato × lunghezza-contesto.
2. **I modelli closed di frontiera hanno davvero chiuso il format tax?** (H4) — Format Tax 2026 lo suggerisce per i vincoli di output; serve replica per il formato di input.
3. **Claude è davvero resiliente a XML *in particolare* sui dati annidati?** (H11) — ImprovingAgents non ha testato Claude; gap critico data la distribuzione di training XML di Anthropic.
4. **Il passaggio di stato in pseudocodice generalizza oltre GAIA L1?** (H16) — la pretesa CodeAgents è grande e cambierebbe l'economia del multi-agente se si replicasse.
5. **Il vantaggio di YAML su JSON con Gemini e GPT-Nano regge sui frontiera closed?** (H17, estensione H10) — Gemini 3 Pro e Claude Opus 4.8 non testati.
6. **La scoperta Checksum "JSON vince la creativa" è reale o rumore a N=10?** (H7) — N=30 con giudice cross-vendor lo dirà.
7. **La tesi OpenAI GPT-4.1 "JSON rende male nel contesto lungo" si replica su Gemini e Claude?** (H14) — affermazione generica che potrebbe essere model-specific.

---

## 8. Regole decisionali compatte per l'articolo

Le regole che l'articolo può cristallizzare, ciascuna con l'ancora di evidenza più forte.

- **Formato input di default su Claude:** tag XML per il partizionamento; Markdown per la prosa. **Ancora:** doc Anthropic; Tam 2024 (Claude XML-native).
- **Formato input di default su GPT:** sezioni Markdown; passa a XML per il wrapping di documenti a contesto lungo. **Ancora:** guida OpenAI GPT-4.1; He et al. 2024.
- **Formato input di default su Gemini:** Markdown con delimitatori `##`; tag XML per gli esempi; istruzioni alla fine. **Ancora:** doc Gemini; ImprovingAgents.
- **Formato per payload di dati annidati:** YAML o heading Markdown — non JSON, mai XML per nesting profondo salvo su Claude. **Ancora:** ImprovingAgents ott 2025.
- **Output strutturato:** sempre Structured Outputs nativi / tool-mode strict; mai sola istruzione di prompt per il JSON. **Ancora:** pretesa OpenAI 100%; JSONSchemaBench; Tam 2024.
- **Ragionamento + output strutturato:** due passi — ragiona free-form, poi converti. **Ancora:** Tam 2024; Format Tax 2026.
- **RAG a contesto lungo:** wrapper XML `<document><source>`; query alla fine; grounding quote-first. **Ancora:** doc Anthropic; Liu 2023; Chroma 2025.
- **Intuizione sul costo in token:** Markdown 1,0× → YAML 1,1× → JSON 1,5× → XML 1,8×; i token di output costano 4–8× quelli di input. **Ancora:** ImprovingAgents; prezzi dei vendor.
- **Sicurezza:** togli i link-immagine Markdown da ogni output che possa includere contenuto controllato da un attaccante; usa tag XML con sale per i blocchi di contenuto non fidato; non fidarti del constrained decoding per fermare l'injection. **Ancora:** Willison; AWS; Schneidenbach; OWASP.
- **Effetto della dimensione del modello:** i modelli open-weight piccoli mostrano effetti di formato ampi; i frontiera closed sono per lo più robusti. **Ancora:** Format Tax 2026; He et al. 2024.

---

*Fine knowledge base v3.1. Modifica rispetto a v3: rimosso D7 come esperimento separato e assorbito dentro D5 come ipotesi secondaria (la domanda "su Claude XML non è il peggiore sui dati annidati" si valuta filtrando i risultati di D5 sui modelli Claude, senza chiamate aggiuntive: D5 e D7 usavano la stessa suite, la stessa variabile e gli stessi formati, quindi erano ridondanti). Esperimenti ora 11 anziché 12. Modifiche di v3 rispetto a v2: aggiunto Qwen2.5 (via Ollama) come sesto modello open-weight/locale; parametro effort/reasoning fissato a medio per tutti gli esperimenti tranne D3 e D4, dove è variabile a tre livelli; D2/D5/D8/D9 estesi ai formati applicabili (cinque non-tabellari) su tutti e sei i modelli; D3/D4/D6/D10 estesi mantenendo l'impostazione Q-OUT precedente (JSON nativo-strict vs altri formati via istruzione testuale); D7tab mantenuto; D14 (formati misti) rimosso; regola di applicabilità dei formati per tipo di contenuto (sette completi solo sui task tabellari, cinque non-tabellari altrove); limite del protocollo riscritto per riflettere la presenza di un modello open-weight. Ogni affermazione numerica va verificata contro la fonte primaria citata prima della pubblicazione. Le pretese "OpenAI 73%" e "Anthropic 20–40% XML" non vanno propagate senza una fonte primaria.*
