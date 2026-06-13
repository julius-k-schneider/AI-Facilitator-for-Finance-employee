export const HALLUZINATIONEN_LERNCHECK = {
  id: 'lerncheck-halluzinationen',
  title: 'Lerncheck: Halluzinationen erkennen',
  description: 'Lies den Text und beantworte die Fragen, um zu prüfen, ob du AI-Halluzinationen erkennen kannst.',
  category: 'AI Grundlagen',
  difficulty: 'Medium',
  estimatedTime: '8 Min.',
  maxPoints: 100,

  text: `
## Was sind AI-Halluzinationen?

AI-Sprachmodelle wie ChatGPT oder Claude können manchmal Informationen erfinden, die überzeugend klingen, aber falsch sind. Dieses Phänomen nennt man **Halluzination**.

Im Finanzbereich ist das besonders gefährlich. Ein AI-Modell könnte zum Beispiel eine Zahl im Jahresbericht falsch angeben, einen nicht existierenden Gesetzesartikel zitieren oder eine Berechnung mit einem erfundenen Ergebnis präsentieren.

### Warum passiert das?

AI-Modelle generieren Text, indem sie das wahrscheinlichste nächste Wort vorhersagen. Sie "wissen" nicht, ob eine Information wahr ist — sie erzeugen Text, der plausibel klingt. Wenn das Modell unsicher ist, kann es eine überzeugende aber falsche Antwort produzieren.

### Wie erkenne ich eine Halluzination?

Es gibt einige Warnsignale:
- **Sehr spezifische Zahlen** ohne Quellenangabe
- **Gesetzesartikel oder Normen**, die du nicht kennst
- **Zitate**, die du nicht verifizieren kannst
- **Berechnungen**, die du nicht nachgeprüft hast

### Was tun?

Überprüfe immer AI-generierte Zahlen, Zitate und Quellenangaben bevor du sie in offiziellen Berichten verwendest. Nutze AI als Hilfsmittel, nicht als einzige Quelle.
  `,

  questions: [
    {
      question: 'Was versteht man unter einer AI-Halluzination?',
      options: [
        'Ein technischer Fehler, bei dem die AI abstürzt',
        'Wenn die AI überzeugende aber falsche Informationen erfindet',
        'Wenn die AI keine Antwort geben kann',
        'Ein Sicherheitsproblem in AI-Systemen',
      ],
      correctIndex: 1,
      explanation: 'Eine Halluzination ist, wenn das AI-Modell plausibel klingende aber faktisch falsche Informationen generiert.',
    },
    {
      question: 'Warum sind Halluzinationen im Finanzbereich besonders gefährlich?',
      options: [
        'Weil AI im Finanzbereich verboten ist',
        'Weil falsche Zahlen oder Gesetzesartikel in Berichten schwerwiegende Folgen haben können',
        'Weil Finanzberichte immer von AI erstellt werden',
        'Weil AI keine Zahlen verarbeiten kann',
      ],
      correctIndex: 1,
      explanation: 'Im Finanzbereich können falsche Zahlen, erfundene Gesetzesartikel oder fehlerhafte Berechnungen zu ernsthaften rechtlichen und finanziellen Konsequenzen führen.',
    },
    {
      question: 'Welches ist ein typisches Warnsignal für eine mögliche Halluzination?',
      options: [
        'Die AI antwortet sehr schnell',
        'Die AI verwendet einfache Sprache',
        'Sehr spezifische Zahlen ohne Quellenangabe',
        'Die AI stellt Rückfragen',
      ],
      correctIndex: 2,
      explanation: 'Sehr spezifische Zahlen ohne nachvollziehbare Quelle sind ein klassisches Warnsignal für eine mögliche Halluzination.',
    },
    {
      question: 'Was sollte man mit AI-generierten Zahlen in offiziellen Berichten tun?',
      options: [
        'Direkt übernehmen, da AI immer korrekt ist',
        'Immer vor der Verwendung überprüfen und verifizieren',
        'Nur bei langen Berichten prüfen',
        'Die Zahlen mit 10% Puffer verwenden',
      ],
      correctIndex: 1,
      explanation: 'AI-generierte Zahlen, Zitate und Quellenangaben sollten immer vor der Verwendung in offiziellen Dokumenten überprüft werden.',
    },
  ],
}