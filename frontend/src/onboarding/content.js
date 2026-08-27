/**
 * Hardcoded onboarding content.
 *
 * The onboarding is static and not role-specific, so the content deliberately
 * lives here in the frontend (not in the Django admin). The info and question
 * structures follow the same schema that `InfoView`/`Quiz` render and that is
 * later reused for AI-generated daily challenges.
 *
 * Each chapter has a German and an English variant (`{ de, en }`).
 * `pickLang()` selects based on the active i18n language (fallback German).
 */

export const PASS_THRESHOLD = 0.8

export function pickLang(node, lang) {
  if (!node) return node
  return node[lang] ?? node.de
}

export const ONBOARDING = {
  passThreshold: PASS_THRESHOLD,
  chapters: [
    {
      id: 'ai-basics',
      title: { de: 'KI- & LLM-Grundlagen', en: 'AI & LLM basics' },
      summary: {
        de: 'Wie ein LLM Antworten erzeugt, was es nicht weiß und wo seine Grenzen liegen.',
        en: 'How an LLM produces answers, what it does not know and where its limits are.',
      },
      info: {
        de: [
          { type: 'heading', text: 'Was ist KI – und was ein LLM?' },
          {
            type: 'paragraph',
            text: 'Künstliche Intelligenz (KI) beschreibt Systeme, die Aufgaben lösen, für die man früher menschliches Denken brauchte. Im Arbeitsalltag begegnet dir KI heute vor allem in Form von „Large Language Models" (LLMs) wie den Modellen hinter ChatGPT oder Claude.',
          },
          {
            type: 'paragraph',
            text: 'Ein LLM ist im Kern ein sehr leistungsfähiger Textvorhersager: Es schätzt auf Basis riesiger Textmengen, welches Wort als nächstes am wahrscheinlichsten passt – und erzeugt so flüssige Antworten, Zusammenfassungen oder Analysen. Es schlägt nichts nach und ruft nichts ab, sondern formuliert jede Antwort neu. Genau daraus ergeben sich seine Stärken und seine Schwächen.',
          },
          { type: 'heading', text: 'Drei Eigenheiten, die deinen Alltag bestimmen' },
          {
            type: 'list',
            ordered: true,
            items: [
              'Trainingsstand: Das Modell kennt nur Texte bis zu einem bestimmten Stichtag. Eure internen Zahlen, Richtlinien und Systeme kennt es gar nicht – außer du gibst sie ihm im Chat mit.',
              'Kontextfenster: Ein Chat hat eine begrenzte „Merkspanne". In sehr langen Unterhaltungen rutschen frühe Angaben aus dem Blick – wichtige Vorgaben lieber wiederholen.',
              'Keine feste Antwort: Dieselbe Frage kann zweimal unterschiedlich beantwortet werden. Dass zwei Antworten übereinstimmen, ist deshalb kein Beleg dafür, dass sie stimmen.',
            ],
          },
          {
            type: 'paragraph',
            text: 'Ein LLM ist auch keine Suchmaschine. Eine Suchmaschine verweist auf Quellen, die du selbst nachlesen kannst; ein LLM formuliert eine Antwort, die plausibel klingt – mit oder ohne belastbare Grundlage. Manche Tools kombinieren beides und recherchieren live, dann erkennst du das an mitgelieferten Quellenlinks.',
          },
          {
            type: 'list',
            items: [
              'Stark bei: Formulieren, Umformulieren, Zusammenfassen, Strukturieren, Erklären, Ideen sammeln, Textentwürfe, Excel- und Formelhilfe.',
              'Schwach bei: exaktem Rechnen über viele Schritte, aktuellen oder internen Zahlen, rechtssicheren Aussagen, allem, wofür jemand geradestehen muss.',
            ],
          },
          {
            type: 'callout',
            variant: 'info',
            title: 'Im Finance-Alltag heißt das',
            text: 'Lass dir einen Abweichungskommentar formulieren, aber liefere die Zahlen selbst mit – und prüfe sie am Ende gegen dein Reporting. Die Sprache kommt vom Modell, die Zahlen von dir.',
          },
          {
            type: 'callout',
            variant: 'tip',
            title: 'Merke',
            text: 'Ein LLM ist ein Assistent, kein Orakel. Es unterstützt dich – die fachliche Verantwortung bleibt bei dir.',
          },
        ],
        en: [
          { type: 'heading', text: 'What is AI – and what is an LLM?' },
          {
            type: 'paragraph',
            text: 'Artificial intelligence (AI) describes systems that solve tasks which used to require human thinking. At work, you mostly encounter AI today as "large language models" (LLMs) like the models behind ChatGPT or Claude.',
          },
          {
            type: 'paragraph',
            text: 'At its core, an LLM is a very capable text predictor: based on huge amounts of text it estimates which word is most likely to come next – producing fluent answers, summaries or analyses. It does not look anything up or retrieve stored answers; it composes every reply from scratch. That is exactly where its strengths and its weaknesses come from.',
          },
          { type: 'heading', text: 'Three traits that shape your daily work' },
          {
            type: 'list',
            ordered: true,
            items: [
              'Training cut-off: the model only knows texts up to a certain date. It does not know your internal figures, policies or systems at all – unless you provide them in the chat.',
              'Context window: a chat has a limited "memory span". In very long conversations, early details drop out of view – better repeat important requirements.',
              'No fixed answer: the same question can be answered differently twice. Two matching answers are therefore no proof that either one is correct.',
            ],
          },
          {
            type: 'paragraph',
            text: 'An LLM is not a search engine either. A search engine points to sources you can read yourself; an LLM formulates an answer that sounds plausible – with or without a solid basis. Some tools combine both and search live; you recognise that by the source links they include.',
          },
          {
            type: 'list',
            items: [
              'Strong at: drafting, rewriting, summarising, structuring, explaining, collecting ideas, first drafts, spreadsheet and formula help.',
              'Weak at: exact multi-step arithmetic, current or internal figures, legally binding statements, anything someone has to answer for.',
            ],
          },
          {
            type: 'callout',
            variant: 'info',
            title: 'What that means in finance',
            text: 'Have it draft a variance comment, but supply the figures yourself – and check them against your reporting at the end. The wording comes from the model, the numbers come from you.',
          },
          {
            type: 'callout',
            variant: 'tip',
            title: 'Remember',
            text: 'An LLM is an assistant, not an oracle. It supports you – the professional responsibility stays with you.',
          },
        ],
      },
      quiz: {
        de: [
          {
            id: 'ai-basics-q1',
            question: 'Wie lässt sich ein LLM am treffendsten beschreiben?',
            choices: [
              'Eine Datenbank mit garantiert korrekten Fakten',
              'Ein System, das auf Basis von Mustern das wahrscheinlich nächste Wort vorhersagt',
              'Ein Programm, das live im Internet recherchiert',
            ],
            correctIndex: 1,
            explanation:
              'Ein LLM erzeugt Text, indem es Muster aus Trainingsdaten nutzt, um das wahrscheinlich nächste Wort vorherzusagen – es ist keine Faktendatenbank.',
          },
          {
            id: 'ai-basics-q2',
            question: 'Du fragst ein KI-Tool nach dem aktuellen Quartalsumsatz eures Unternehmens. Warum ist die Antwort mit Vorsicht zu genießen?',
            choices: [
              'Weil das Modell für so große Zahlen zu ungenau rechnet',
              'Weil das Modell eure internen Zahlen nicht kennt und nur bis zu einem Trainingsstichtag gelernt hat',
              'Weil solche Fragen technisch nicht beantwortet werden können',
            ],
            correctIndex: 1,
            explanation:
              'Interne Zahlen sind nicht Teil der Trainingsdaten, und der Trainingsstand liegt in der Vergangenheit. Ohne dass du die Zahlen mitlieferst, kann das Modell sie nur erfinden.',
          },
          {
            id: 'ai-basics-q3',
            question: 'Du stellst dieselbe Frage zweimal und bekommst zwei unterschiedlich formulierte Antworten. Wie ordnest du das ein?',
            choices: [
              'Das ist normal – Antworten werden jedes Mal neu erzeugt, nicht abgerufen',
              'Das Tool hat einen Fehler und sollte gemeldet werden',
              'Die zweite Antwort ist immer die bessere',
            ],
            correctIndex: 0,
            explanation:
              'Ein LLM formuliert jede Antwort neu, deshalb variieren Ergebnisse. Umgekehrt gilt: Auch zwei gleichlautende Antworten sind kein Beleg für Richtigkeit.',
          },
        ],
        en: [
          {
            id: 'ai-basics-q1',
            question: 'Which description fits an LLM best?',
            choices: [
              'A database with guaranteed correct facts',
              'A system that predicts the likely next word based on patterns',
              'A program that researches live on the internet',
            ],
            correctIndex: 1,
            explanation:
              'An LLM generates text by using patterns from training data to predict the likely next word – it is not a fact database.',
          },
          {
            id: 'ai-basics-q2',
            question: 'You ask an AI tool for your company’s current quarterly revenue. Why should you treat the answer with caution?',
            choices: [
              'Because the model is too imprecise to calculate with such large numbers',
              'Because the model does not know your internal figures and only learned up to a training cut-off',
              'Because such questions cannot be answered technically',
            ],
            correctIndex: 1,
            explanation:
              'Internal figures are not part of the training data, and the training cut-off lies in the past. Unless you supply the numbers, the model can only invent them.',
          },
          {
            id: 'ai-basics-q3',
            question: 'You ask the same question twice and get two differently worded answers. How do you read that?',
            choices: [
              'That is normal – answers are composed fresh each time, not retrieved',
              'The tool has a bug and should be reported',
              'The second answer is always the better one',
            ],
            correctIndex: 0,
            explanation:
              'An LLM composes every answer anew, so results vary. Conversely: two identical answers are no proof of correctness either.',
          },
        ],
      },
    },
    {
      id: 'prompting',
      title: { de: 'Gute Prompts schreiben', en: 'Writing good prompts' },
      summary: {
        de: 'Rolle, Kontext, Aufgabe und Format – und wie du eine Antwort nachschärfst.',
        en: 'Role, context, task and format – and how to sharpen an answer.',
      },
      info: {
        de: [
          { type: 'heading', text: 'Gute Prompts schreiben' },
          {
            type: 'paragraph',
            text: 'Ein „Prompt" ist deine Anweisung an das Modell. Das Modell rät nicht, was du gemeint hast – es arbeitet mit dem, was dasteht. Deshalb entscheidet der Prompt fast immer darüber, ob eine Antwort brauchbar ist oder nur allgemein klingt.',
          },
          { type: 'heading', text: 'Vier Bausteine, die fast immer helfen' },
          {
            type: 'list',
            ordered: true,
            items: [
              'Rolle: Aus welcher Perspektive soll geantwortet werden? („Du bist Controller in einem mittelständischen Industrieunternehmen.")',
              'Kontext: Worum geht es, für wen ist das Ergebnis, welche Zahlen und Rahmenbedingungen gelten?',
              'Aufgabe: Was genau soll entstehen – erklären, zusammenfassen, entwerfen, prüfen?',
              'Format: Stichpunkte oder Fließtext, Länge, Tonalität, Sprache, Struktur.',
            ],
          },
          {
            type: 'paragraph',
            text: 'Der Unterschied ist größer, als man denkt. „Erkläre Abschreibungen" liefert einen Lexikontext. Mit Rolle, Kontext, Aufgabe und Format bekommst du etwas, das du fast direkt weiterverwenden kannst.',
          },
          {
            type: 'callout',
            variant: 'info',
            title: 'Schwach vs. stark',
            text: 'Schwach: „Schreib was zur Umsatzabweichung." – Stark: „Du bist Controller. Der Umsatz liegt im Juli 4,2 % unter Plan, Hauptursache ist ein verschobener Großauftrag. Formuliere einen Kommentar für das Monatsreporting an die Geschäftsführung: 3 Sätze, sachlich, ohne Spekulation über Folgemonate."',
          },
          {
            type: 'paragraph',
            text: 'Wenn Stil oder Struktur nicht passen, hilft ein Beispiel mehr als jede Beschreibung: Gib einen früheren Kommentar mit und schreibe dazu „orientiere dich an Aufbau und Tonalität dieses Beispiels".',
          },
          {
            type: 'paragraph',
            text: 'Und der wichtigste Punkt: Der erste Prompt muss nicht perfekt sein. Arbeite im selben Chat weiter und schärfe nach – „kürzer", „ohne Fachbegriffe", „nenne die Annahme explizit". Das ist schneller und besser, als die Frage neu zu stellen und auf ein anderes Ergebnis zu hoffen.',
          },
          {
            type: 'callout',
            variant: 'tip',
            title: 'Vorlage zum Kopieren',
            text: 'Rolle: Du bist … | Kontext: … | Aufgabe: … | Format: … | Wichtig: Wenn dir Informationen fehlen, frage nach, statt zu raten.',
          },
        ],
        en: [
          { type: 'heading', text: 'Writing good prompts' },
          {
            type: 'paragraph',
            text: 'A "prompt" is your instruction to the model. The model does not guess what you meant – it works with what is written. That is why the prompt almost always decides whether an answer is usable or merely sounds generic.',
          },
          { type: 'heading', text: 'Four building blocks that almost always help' },
          {
            type: 'list',
            ordered: true,
            items: [
              'Role: from which perspective should it answer? ("You are a controller at a mid-sized industrial company.")',
              'Context: what is it about, who is the result for, which figures and constraints apply?',
              'Task: what exactly should be produced – explain, summarise, draft, review?',
              'Format: bullet points or prose, length, tone, language, structure.',
            ],
          },
          {
            type: 'paragraph',
            text: 'The difference is bigger than you would expect. "Explain depreciation" gives you an encyclopedia entry. With role, context, task and format you get something you can almost use as is.',
          },
          {
            type: 'callout',
            variant: 'info',
            title: 'Weak vs. strong',
            text: 'Weak: "Write something about the revenue variance." – Strong: "You are a controller. July revenue is 4.2% below plan, mainly because a major order was postponed. Draft a comment for the monthly report to management: 3 sentences, factual, no speculation about coming months."',
          },
          {
            type: 'paragraph',
            text: 'When the style or structure is off, an example helps more than any description: paste in an earlier comment and add "follow the structure and tone of this example".',
          },
          {
            type: 'paragraph',
            text: 'And the most important point: your first prompt does not have to be perfect. Keep working in the same chat and sharpen the result – "shorter", "no jargon", "state the assumption explicitly". That is faster and better than asking again and hoping for a different outcome.',
          },
          {
            type: 'callout',
            variant: 'tip',
            title: 'Template to copy',
            text: 'Role: You are … | Context: … | Task: … | Format: … | Important: if information is missing, ask instead of guessing.',
          },
        ],
      },
      quiz: {
        de: [
          {
            id: 'prompting-q1',
            question: 'Was macht einen Prompt in der Regel besser?',
            choices: [
              'Möglichst kurz und allgemein halten',
              'Rolle, Kontext, konkrete Aufgabe und gewünschtes Format angeben',
              'Dem Modell keine Vorgaben machen, damit es kreativ bleibt',
            ],
            correctIndex: 1,
            explanation:
              'Rolle, klarer Kontext, eine präzise Aufgabe und ein vorgegebenes Format führen zu deutlich nützlicheren Antworten.',
          },
          {
            id: 'prompting-q2',
            question: 'Die erste Antwort ist zu allgemein und zu lang. Was ist der beste nächste Schritt?',
            choices: [
              'Im selben Chat nachschärfen: kürzen lassen, Kontext ergänzen, Format vorgeben',
              'Exakt dieselbe Frage noch einmal stellen',
              'Die Antwort so übernehmen und selbst zusammenstreichen',
            ],
            correctIndex: 0,
            explanation:
              'Nachschärfen im laufenden Chat ist der schnellste Weg: Das Modell behält den Kontext und du korrigierst gezielt Länge, Tiefe und Format.',
          },
          {
            id: 'prompting-q3',
            question: 'Der Text ist inhaltlich richtig, klingt aber gar nicht nach euren Berichten. Was hilft am meisten?',
            choices: [
              'Ein bis zwei frühere Kommentare als Beispiel mitgeben und darauf verweisen',
              'Das Modell bitten, „professioneller" zu schreiben',
              'Auf ein anderes KI-Tool wechseln',
            ],
            correctIndex: 0,
            explanation:
              'Konkrete Beispiele wirken stärker als abstrakte Stilwünsche – das Modell übernimmt Aufbau und Tonalität aus dem, was du zeigst.',
          },
        ],
        en: [
          {
            id: 'prompting-q1',
            question: 'What usually makes a prompt better?',
            choices: [
              'Keeping it as short and general as possible',
              'Providing a role, context, a concrete task and the desired format',
              'Giving the model no guidance so it stays creative',
            ],
            correctIndex: 1,
            explanation:
              'A role, clear context, a precise task and a specified format lead to much more useful answers.',
          },
          {
            id: 'prompting-q2',
            question: 'The first answer is too generic and too long. What is the best next step?',
            choices: [
              'Sharpen it in the same chat: ask for it shorter, add context, specify the format',
              'Ask exactly the same question again',
              'Take the answer as is and cut it down yourself',
            ],
            correctIndex: 0,
            explanation:
              'Refining within the running chat is fastest: the model keeps the context and you correct length, depth and format on purpose.',
          },
          {
            id: 'prompting-q3',
            question: 'The text is factually right but sounds nothing like your reports. What helps most?',
            choices: [
              'Provide one or two earlier comments as an example and point to them',
              'Ask the model to write "more professionally"',
              'Switch to a different AI tool',
            ],
            correctIndex: 0,
            explanation:
              'Concrete examples work better than abstract style requests – the model picks up structure and tone from what you show it.',
          },
        ],
      },
    },
    {
      id: 'safe-use',
      title: { de: 'Sicherer Umgang', en: 'Safe use' },
      summary: {
        de: 'Halluzinationen erkennen, Ergebnisse prüfen und vertrauliche Daten schützen.',
        en: 'Spot hallucinations, verify results and protect confidential data.',
      },
      info: {
        de: [
          { type: 'heading', text: 'Sicherer & verantwortungsvoller Umgang' },
          {
            type: 'paragraph',
            text: 'KI-Werkzeuge sind im Finance-Bereich besonders nützlich – aber sie bringen Risiken mit, die du kennen musst. Zwei davon sind zentral: Halluzinationen und Datenschutz.',
          },
          {
            type: 'paragraph',
            text: 'Eine „Halluzination" ist eine erfundene, aber überzeugend klingende Aussage. Das Modell signalisiert dabei keine Unsicherheit: Der erfundene Paragraf steht im selben sicheren Ton da wie eine korrekte Angabe. Genau deshalb fallen Fehler im Fließtext so selten auf.',
          },
          {
            type: 'list',
            items: [
              'Erfundene Paragrafen, Normen oder Fristen – oft mit korrekt klingender Nummer.',
              'Quellen und Studien, die es nicht gibt, oder Zitate, die so nie gefallen sind.',
              'Kennzahlen-Definitionen, die von eurer internen Definition abweichen.',
              'Rechenfehler in mehrstufigen Rechnungen, während das Ergebnis sauber formatiert aussieht.',
            ],
          },
          { type: 'heading', text: 'So prüfst du ein Ergebnis' },
          {
            type: 'list',
            ordered: true,
            items: [
              'Zahlen selbst nachrechnen – nicht das Modell fragen, ob es sicher ist.',
              'Quellen, Paragrafen und Fristen im Original nachschlagen.',
              'Plausibilität gegen deine Erfahrung und die Vorperiode prüfen.',
              'Im Zweifel den Fachbereich oder eine Kollegin gegenlesen lassen.',
            ],
          },
          {
            type: 'paragraph',
            text: 'Der zweite Punkt ist der Umgang mit Daten. Alles, was du in ein KI-Tool eingibst, verlässt in der Regel euer Haus und kann dort gespeichert werden. Personenbezogene Daten (Gehälter, Namen, Krankheitszeiten) und Geschäftsgeheimnisse (Kalkulationen, Verträge, unveröffentlichte Zahlen) gehören deshalb nur in Tools, die dafür freigegeben sind.',
          },
          {
            type: 'callout',
            variant: 'warning',
            title: 'Achtung',
            text: 'Gib niemals vertrauliche Personen- oder Geschäftsdaten in nicht freigegebene Tools ein. Wenn du Hilfe bei einer Auswertung brauchst, entferne vorher Namen und Identifikatoren oder arbeite mit anonymisierten Beispielwerten.',
          },
          {
            type: 'callout',
            variant: 'tip',
            title: 'Merke',
            text: 'Unter dem Ergebnis steht am Ende dein Name, nicht der des Modells. KI darf dir Arbeit abnehmen – die Prüfung und die Verantwortung nicht.',
          },
        ],
        en: [
          { type: 'heading', text: 'Safe & responsible use' },
          {
            type: 'paragraph',
            text: 'AI tools are particularly useful in finance – but they come with risks you must be aware of. Two are key: hallucinations and data protection.',
          },
          {
            type: 'paragraph',
            text: 'A "hallucination" is a fabricated but convincing-sounding statement. The model gives no signal of uncertainty: an invented paragraph appears in exactly the same confident tone as a correct one. That is why such errors are so easy to miss inside fluent prose.',
          },
          {
            type: 'list',
            items: [
              'Invented paragraphs, standards or deadlines – often with a plausible-looking number.',
              'Sources and studies that do not exist, or quotes that were never said.',
              'Metric definitions that differ from your internal definition.',
              'Arithmetic errors in multi-step calculations, while the result looks neatly formatted.',
            ],
          },
          { type: 'heading', text: 'How to check a result' },
          {
            type: 'list',
            ordered: true,
            items: [
              'Recalculate the numbers yourself – do not ask the model whether it is sure.',
              'Look up sources, paragraphs and deadlines in the original.',
              'Sanity-check against your own experience and the prior period.',
              'When in doubt, have the department or a colleague review it.',
            ],
          },
          {
            type: 'paragraph',
            text: 'The second point is how you handle data. Anything you type into an AI tool usually leaves your company and may be stored there. Personal data (salaries, names, sick leave) and business secrets (costings, contracts, unpublished figures) therefore belong only in tools that are approved for it.',
          },
          {
            type: 'callout',
            variant: 'warning',
            title: 'Caution',
            text: 'Never enter confidential personal or business data into non-approved tools. If you need help with an analysis, remove names and identifiers first or work with anonymised sample values.',
          },
          {
            type: 'callout',
            variant: 'tip',
            title: 'Remember',
            text: 'In the end it is your name under the result, not the model’s. AI may take work off your hands – the review and the responsibility stay with you.',
          },
        ],
      },
      quiz: {
        de: [
          {
            id: 'safe-use-q1',
            question: 'Das Modell nennt dir eine konkrete Gesetzesregelung mit Paragraf. Was tust du?',
            choices: [
              'Direkt übernehmen – das Modell wird schon recht haben',
              'Die Angabe vor der Verwendung in einer verlässlichen Quelle prüfen',
              'Das Modell einfach noch zweimal dasselbe fragen',
            ],
            correctIndex: 1,
            explanation:
              'Modelle können Regelungen und Quellen erfinden (Halluzination). Fachlich relevante Angaben gehören immer geprüft.',
          },
          {
            id: 'safe-use-q2',
            question: 'Du möchtest eine Gehaltsliste mit Namen von einem KI-Tool auswerten lassen, das intern nicht freigegeben ist. Wie gehst du vor?',
            choices: [
              'Gar nicht – nur freigegebene Tools nutzen und personenbezogene Daten vorher entfernen',
              'Hochladen ist okay, solange du den Chat danach löschst',
              'Hochladen ist okay, weil die Auswertung ja intern bleibt',
            ],
            correctIndex: 0,
            explanation:
              'Eingaben verlassen euer Haus und können gespeichert werden. Personenbezogene Daten gehören nur in freigegebene Tools – und auch dort möglichst anonymisiert.',
          },
          {
            id: 'safe-use-q3',
            question: 'Das Modell liefert eine saubere Abweichungsanalyse mit Zwischensummen. Was machst du vor dem Versand?',
            choices: [
              'Die Zahlen selbst nachrechnen und gegen das Reporting abgleichen',
              'Übernehmen – die Zwischensummen sehen plausibel aus',
              'Das Modell fragen, ob die Rechnung stimmt',
            ],
            correctIndex: 0,
            explanation:
              'Mehrstufige Rechnungen sind eine typische Fehlerquelle, und eine saubere Formatierung sagt nichts über die Richtigkeit. Auch die Rückfrage ans Modell ersetzt keine Prüfung.',
          },
        ],
        en: [
          {
            id: 'safe-use-q1',
            question: 'The model gives you a specific legal rule with a paragraph number. What do you do?',
            choices: [
              'Use it directly – the model is probably right',
              'Verify the statement in a reliable source before using it',
              'Just ask the model the same thing two more times',
            ],
            correctIndex: 1,
            explanation:
              'Models can invent rules and sources (hallucination). Professionally relevant statements must always be verified.',
          },
          {
            id: 'safe-use-q2',
            question: 'You want a non-approved AI tool to analyse a salary list containing names. How do you proceed?',
            choices: [
              'Not at all – use approved tools only and strip personal data beforehand',
              'Uploading is fine as long as you delete the chat afterwards',
              'Uploading is fine because the analysis stays internal anyway',
            ],
            correctIndex: 0,
            explanation:
              'Your input leaves the company and may be stored. Personal data belongs only in approved tools – and even there, anonymised where possible.',
          },
          {
            id: 'safe-use-q3',
            question: 'The model delivers a tidy variance analysis with subtotals. What do you do before sending it out?',
            choices: [
              'Recalculate the figures yourself and reconcile them with the reporting',
              'Use it – the subtotals look plausible',
              'Ask the model whether the calculation is correct',
            ],
            correctIndex: 0,
            explanation:
              'Multi-step calculations are a classic source of errors, and neat formatting says nothing about correctness. Asking the model back is no substitute for checking.',
          },
        ],
      },
    },
  ],
}
