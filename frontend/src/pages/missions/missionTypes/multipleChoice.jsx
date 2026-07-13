import { choiceDefinition } from './shared'

export default choiceDefinition({
  id: 'multiple_choice', labelKey: 'multipleChoice', multiple: true,
  example: (text) => ({
    id: 'test-multiple', type: 'multiple_choice', title: text('Gute Prompt-Bestandteile', 'Good prompt elements'),
    description: text('Wähle hilfreiche Bestandteile eines Finance-Prompts.', 'Choose useful elements of a finance prompt.'),
    max_points: 30, completed: false, score: null,
    content: { question: text('Welche Angaben verbessern den Prompt?', 'Which details improve the prompt?'), options: [text('Klares Ziel', 'Clear goal'), text('Gewünschtes Ausgabeformat', 'Desired output format'), text('Möglichst wenig Kontext', 'As little context as possible')] },
    test_solution: {
      correct_indices: [0, 1],
      micro_learning: text('Ein Prompt ist wie ein Arbeitsauftrag. Wenn Ziel, Hintergrund und gewünschte Form fehlen, muss die AI Annahmen treffen. Gute Prompts reduzieren diese Annahmen und machen Ergebnisse vergleichbarer.', 'A prompt works like a work instruction. If the goal, background, and desired format are missing, the AI has to make assumptions. Good prompts reduce those assumptions and make results easier to compare.'),
    },
  }),
})
