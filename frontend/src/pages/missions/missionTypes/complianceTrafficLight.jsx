/* eslint-disable react-refresh/only-export-components */
import { Badge, Group, Paper, Radio, Select, Stack, Text, Textarea, TextInput } from '@mantine/core'

const emptyStatements = () => Array.from({ length: 3 }, () => ({ de: '', en: '', correct_color: 'green', feedback_de: '', feedback_en: '' }))

function Runner({ mission, answer, setAnswer, result, t }) {
  return <Stack gap="md">{mission.content.statements.map((statement, index) => <Paper key={index} withBorder radius="md" p="md"><Stack gap="sm"><Text fw={600}>{index + 1}. {statement}</Text><Radio.Group value={answer[index]} onChange={(value) => setAnswer((current) => current.map((item, itemIndex) => itemIndex === index ? value : item))}><Group grow>{['green', 'yellow', 'red'].map((color) => <Paper key={color} withBorder radius="md" p="xs"><Radio value={color} color={color === 'yellow' ? 'orange' : color} label={t(`missions.trafficLight.${color}`)} disabled={Boolean(result)} /></Paper>)}</Group></Radio.Group></Stack></Paper>)}</Stack>
}

function Editor({ form, setForm, t }) {
  const setStatement = (index, field, value) => setForm((current) => ({ ...current, statements: current.statements.map((statement, statementIndex) => statementIndex === index ? { ...statement, [field]: value } : statement) }))
  return <Stack gap="sm"><Text fw={700}>{t('missions.creator.statements')}</Text>{form.statements.map((statement, index) => <Paper key={index} withBorder radius="md" p="sm"><Stack gap="sm"><Group grow><TextInput label={`DE ${index + 1}`} value={statement.de} onChange={(event) => setStatement(index, 'de', event.target.value)} /><TextInput label={`EN ${index + 1}`} value={statement.en} onChange={(event) => setStatement(index, 'en', event.target.value)} /></Group><Select label={t('missions.creator.correctColor')} value={statement.correct_color} data={['green', 'yellow', 'red'].map((color) => ({ value: color, label: t(`missions.trafficLight.${color}`) }))} onChange={(value) => setStatement(index, 'correct_color', value)} /><Group grow><Textarea label={t('missions.creator.feedbackDe')} value={statement.feedback_de} onChange={(event) => setStatement(index, 'feedback_de', event.target.value)} /><Textarea label={t('missions.creator.feedbackEn')} value={statement.feedback_en} onChange={(event) => setStatement(index, 'feedback_en', event.target.value)} /></Group></Stack></Paper>)}</Stack>
}

function Solution({ mission, language, showSolution = true, t }) {
  return <Stack gap="xs">{mission.statements.map((statement, index) => <Paper key={index} withBorder radius="md" p="sm"><Text fz="sm" fw={600}>{index + 1}. {statement[language]}</Text>{showSolution && <><Badge mt="xs" color={statement.correct_color === 'yellow' ? 'orange' : statement.correct_color}>{t(`missions.trafficLight.${statement.correct_color}`)}</Badge><Text fz="sm" mt="xs">{statement[`feedback_${language}`]}</Text></>}</Paper>)}</Stack>
}

function ResultDetails({ mission, result, t }) {
  return <Stack gap="xs">{mission.content.statements.map((statement, index) => <Paper key={index} withBorder radius="md" p="sm"><Group gap="xs"><Badge color={result.correct_colors[index] === 'yellow' ? 'orange' : result.correct_colors[index]}>{t(`missions.trafficLight.${result.correct_colors[index]}`)}</Badge><Text fz="sm" fw={600}>{statement}</Text></Group><Text fz="sm" fw={700} c={result.item_correct[index] ? 'green.8' : 'red.7'} mt="xs">{result.item_correct[index] ? t('missions.result.correctPrefix') : t('missions.result.wrongPrefix')}</Text><Text fz="sm" c="dimmed">{result.feedback[index]}</Text></Paper>)}</Stack>
}

export default {
  id: 'compliance_traffic_light', labelKey: 'complianceTrafficLight', hasSharedFeedback: false, createDefaults: () => ({ statements: emptyStatements() }),
  initialAnswer: (mission) => mission.content.statements.map(() => ''), isAnswerComplete: (answer) => answer.every(Boolean),
  Runner, Editor, Solution, ResultDetails,
  evaluateTest: (mission, answer) => { const itemCorrect = answer.map((value, index) => value === mission.test_solution.correct_colors[index]); const correctCount = itemCorrect.filter(Boolean).length; return { correct: correctCount === answer.length, score: Math.floor(mission.max_points * correctCount / answer.length), max_points: mission.max_points, correct_count: correctCount, total_count: answer.length, correct_colors: mission.test_solution.correct_colors, item_correct: itemCorrect, feedback: mission.test_solution.feedback } },
  example: (text) => ({ id: 'test-traffic', type: 'compliance_traffic_light', title: text('Compliance-Ampel', 'Compliance traffic light'), description: text('Bewerte drei kurze AI-Nutzungsszenarien.', 'Assess three short AI usage scenarios.'), max_points: 30, completed: false, score: null, content: { question: text('Welche Ampelfarbe passt jeweils?', 'Which traffic-light color fits each scenario?'), statements: [text('Anonymisierte Summen im freigegebenen Enterprise-Tool.', 'Anonymized totals in an approved enterprise tool.'), text('Vertrauliche Kommentare werden zuerst anonymisiert und anschließend geprüft.', 'Confidential comments are anonymized first and then reviewed.'), text('Personenbezogene Gehaltsdaten in einem öffentlichen AI-Tool.', 'Personal salary data in a public AI tool.')] }, test_solution: { correct_colors: ['green', 'yellow', 'red'], feedback: [text('Freigegebenes Tool und anonymisierte Daten sind grundsätzlich unkritisch.', 'Approved tool and anonymized data are generally acceptable.'), text('Schutzmaßnahmen und Prüfung sind erforderlich.', 'Safeguards and review are required.'), text('Personenbezogene vertrauliche Daten gehören nicht in öffentliche Tools.', 'Personal confidential data must not be entered into public tools.')] } }),
}
