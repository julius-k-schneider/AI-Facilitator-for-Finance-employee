/**
 * Hardcoded Onboarding-Inhalt.
 *
 * Das Onboarding ist statisch und nicht rollenspezifisch, daher liegt der
 * Content bewusst hier im Frontend (nicht im Django-Admin). Die Info- und
 * Frage-Strukturen folgen demselben Schema, das `InfoView`/`Quiz` rendern und
 * das später für KI-generierte Daily Challenges wiederverwendet wird.
 *
 * Pro Kapitel gibt es eine deutsche und eine englische Variante (`{ de, en }`).
 * `pickLang()` wählt anhand der aktiven i18n-Sprache (Fallback Deutsch).
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
        de: 'Was KI ist, wie ein LLM funktioniert und wo seine Grenzen liegen.',
        en: 'What AI is, how an LLM works and where its limits are.',
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
            text: 'Ein LLM ist im Kern ein sehr leistungsfähiger Textvorhersager: Es schätzt auf Basis riesiger Textmengen, welches Wort als nächstes am wahrscheinlichsten passt – und erzeugt so flüssige Antworten, Zusammenfassungen oder Analysen.',
          },
          {
            type: 'list',
            items: [
              'LLMs verstehen Sprache nicht wie ein Mensch, sondern erkennen Muster.',
              'Sie haben kein eigenes Wissen über aktuelle Ereignisse außerhalb ihrer Trainingsdaten.',
              'Sie sind Werkzeuge – die Qualität hängt stark davon ab, wie du sie einsetzt.',
            ],
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
            text: 'At its core, an LLM is a very capable text predictor: based on huge amounts of text it estimates which word is most likely to come next – producing fluent answers, summaries or analyses.',
          },
          {
            type: 'list',
            items: [
              'LLMs do not understand language like a human; they recognise patterns.',
              'They have no inherent knowledge of recent events outside their training data.',
              'They are tools – quality depends heavily on how you use them.',
            ],
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
        ],
      },
    },
    {
      id: 'prompting',
      title: { de: 'Gute Prompts schreiben', en: 'Writing good prompts' },
      summary: {
        de: 'Mit Kontext, klarer Aufgabe und Format zu nützlichen Antworten.',
        en: 'Get useful answers with context, a clear task and a format.',
      },
      info: {
        de: [
          { type: 'heading', text: 'Gute Prompts schreiben' },
          {
            type: 'paragraph',
            text: 'Ein „Prompt" ist deine Anweisung an das Modell. Je klarer du beschreibst, was du willst, desto nützlicher die Antwort. Drei Bausteine helfen fast immer: Kontext, konkrete Aufgabe und gewünschtes Format.',
          },
          {
            type: 'list',
            ordered: true,
            items: [
              'Kontext geben: Wer bist du, worum geht es, für wen ist das Ergebnis?',
              'Aufgabe präzisieren: Was genau soll erstellt werden?',
              'Format vorgeben: Tabelle, Stichpunkte, Länge, Tonalität.',
            ],
          },
          {
            type: 'callout',
            variant: 'info',
            title: 'Beispiel',
            text: 'Statt „Erkläre Abschreibungen" besser: „Erkläre einem neuen Kollegen im Controlling in 3 Stichpunkten den Unterschied zwischen linearer und degressiver Abschreibung."',
          },
        ],
        en: [
          { type: 'heading', text: 'Writing good prompts' },
          {
            type: 'paragraph',
            text: 'A "prompt" is your instruction to the model. The clearer you describe what you want, the more useful the answer. Three building blocks almost always help: context, a concrete task and the desired format.',
          },
          {
            type: 'list',
            ordered: true,
            items: [
              'Give context: who are you, what is it about, who is the result for?',
              'Sharpen the task: what exactly should be produced?',
              'Specify the format: table, bullet points, length, tone.',
            ],
          },
          {
            type: 'callout',
            variant: 'info',
            title: 'Example',
            text: 'Instead of "Explain depreciation" try: "Explain to a new controlling colleague, in 3 bullet points, the difference between straight-line and declining-balance depreciation."',
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
              'Kontext, konkrete Aufgabe und gewünschtes Format angeben',
              'Dem Modell keine Vorgaben machen, damit es kreativ bleibt',
            ],
            correctIndex: 1,
            explanation:
              'Klarer Kontext, eine präzise Aufgabe und ein vorgegebenes Format führen zu deutlich nützlicheren Antworten.',
          },
        ],
        en: [
          {
            id: 'prompting-q1',
            question: 'What usually makes a prompt better?',
            choices: [
              'Keeping it as short and general as possible',
              'Providing context, a concrete task and the desired format',
              'Giving the model no guidance so it stays creative',
            ],
            correctIndex: 1,
            explanation:
              'Clear context, a precise task and a specified format lead to much more useful answers.',
          },
        ],
      },
    },
    {
      id: 'safe-use',
      title: { de: 'Sicherer Umgang', en: 'Safe use' },
      summary: {
        de: 'Halluzinationen erkennen und vertrauliche Daten schützen.',
        en: 'Spot hallucinations and protect confidential data.',
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
            text: 'Eine „Halluzination" ist eine erfundene, aber überzeugend klingende Aussage. Das Modell kann Zahlen, Quellen oder Regelungen schlicht erfinden. Deshalb gilt: fachlich relevante Ergebnisse immer prüfen.',
          },
          {
            type: 'callout',
            variant: 'warning',
            title: 'Achtung',
            text: 'Gib niemals vertrauliche Personen- oder Geschäftsdaten in nicht freigegebene Tools ein. Halte dich an die internen Richtlinien zum Datenschutz.',
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
            text: 'A "hallucination" is a fabricated but convincing-sounding statement. The model can simply invent numbers, sources or regulations. So: always verify results that matter professionally.',
          },
          {
            type: 'callout',
            variant: 'warning',
            title: 'Caution',
            text: 'Never enter confidential personal or business data into non-approved tools. Follow the internal data-protection guidelines.',
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
        ],
      },
    },
  ],
  // Eigenständige Fragen, die alle Kapitel abdecken (Freischalt-Quiz).
  finalQuiz: {
    de: [
      {
        id: 'final-q1',
        question: 'Worauf basiert die Textausgabe eines LLM grundsätzlich?',
        choices: [
          'Auf einer Live-Suche im Internet',
          'Auf der Vorhersage des wahrscheinlich nächsten Wortes anhand von Mustern',
          'Auf einer geprüften Faktendatenbank',
        ],
        correctIndex: 1,
        explanation: 'Ein LLM sagt Muster-basiert das wahrscheinlich nächste Wort voraus.',
      },
      {
        id: 'final-q2',
        question: 'Welche drei Bausteine machen einen Prompt meist besser?',
        choices: [
          'Kontext, konkrete Aufgabe, gewünschtes Format',
          'Möglichst kurz, vage und ohne Vorgaben',
          'Viele Emojis, Großbuchstaben, Ausrufezeichen',
        ],
        correctIndex: 0,
        explanation: 'Kontext, eine präzise Aufgabe und ein klares Format führen zu nützlicheren Antworten.',
      },
      {
        id: 'final-q3',
        question: 'Was ist eine „Halluzination" bei einem LLM?',
        choices: [
          'Ein technischer Absturz des Modells',
          'Eine erfundene, aber überzeugend klingende Aussage',
          'Eine besonders kreative, korrekte Idee',
        ],
        correctIndex: 1,
        explanation: 'Halluzinationen sind erfundene Inhalte – deshalb fachlich relevante Ergebnisse immer prüfen.',
      },
      {
        id: 'final-q4',
        question: 'Wie gehst du mit vertraulichen Geschäftsdaten um?',
        choices: [
          'Nur in freigegebene Tools eingeben und interne Datenschutzregeln befolgen',
          'In jedes beliebige KI-Tool eingeben, Hauptsache schnell',
          'Vorher öffentlich posten, dann analysieren lassen',
        ],
        correctIndex: 0,
        explanation: 'Vertrauliche Daten gehören nur in freigegebene Tools – immer gemäß den internen Richtlinien.',
      },
    ],
    en: [
      {
        id: 'final-q1',
        question: 'What is an LLM’s text output fundamentally based on?',
        choices: [
          'A live search on the internet',
          'Predicting the likely next word based on patterns',
          'A verified fact database',
        ],
        correctIndex: 1,
        explanation: 'An LLM predicts the likely next word based on patterns.',
      },
      {
        id: 'final-q2',
        question: 'Which three building blocks usually make a prompt better?',
        choices: [
          'Context, a concrete task, the desired format',
          'As short, vague and unguided as possible',
          'Lots of emojis, capital letters, exclamation marks',
        ],
        correctIndex: 0,
        explanation: 'Context, a precise task and a clear format lead to more useful answers.',
      },
      {
        id: 'final-q3',
        question: 'What is a "hallucination" in an LLM?',
        choices: [
          'A technical crash of the model',
          'A fabricated but convincing-sounding statement',
          'A particularly creative, correct idea',
        ],
        correctIndex: 1,
        explanation: 'Hallucinations are invented content – so always verify professionally relevant results.',
      },
      {
        id: 'final-q4',
        question: 'How do you handle confidential business data?',
        choices: [
          'Only enter it into approved tools and follow internal data-protection rules',
          'Enter it into any AI tool, as long as it is fast',
          'Post it publicly first, then have it analysed',
        ],
        correctIndex: 0,
        explanation: 'Confidential data belongs only in approved tools – always per the internal guidelines.',
      },
    ],
  },
}
